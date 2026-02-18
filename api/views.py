from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    VideoInfoSerializer, 
    DownloadTaskSerializer, 
    DownloadRequestSerializer,
    ExtractInfoRequestSerializer
)
from videos.services import YouTubeExtractor
from downloads.services import SegmentDownloader
from downloads.tasks import process_download_segment
from downloads.models import DownloadTask
from downloads.validators import DownloadValidator
from downloads.progress import ProgressTracker
from videos.models import VideoInfo
import logging

logger = logging.getLogger(__name__)

class VideoInfoView(APIView):
    """
    POST /api/extract-info/
    Extract video metadata and formats
    """
    def post(self, request):
        serializer = ExtractInfoRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        youtube_url = serializer.validated_data['youtube_url']
        
        # 1. Validate URL
        if not DownloadValidator.validate_youtube_url(youtube_url):
            return Response({"error": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # 2. Extract Info
            video_data = YouTubeExtractor.get_video_info(youtube_url)
            
            # 3. Serialize Response
            # Since video_data is a dict but matches serializer structure OR we can use the model instance if saved
            # The service returns a dict, but also saves/updates the model.
            # Let's fetch the model instance to be consistent with serializer
            from videos.models import VideoInfo
            video_instance = VideoInfo.objects.get(youtube_id=video_data['youtube_id'])
            
            response_serializer = VideoInfoSerializer(video_instance)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DownloadSegmentView(APIView):
    """
    POST /api/download-segment/
    Start a background download task
    """
    def post(self, request):
        serializer = DownloadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        youtube_url = data['youtube_url']
        start_time = data['start_time']
        end_time = data['end_time']
        quality = data['quality']
        
        # 1. Get Video Info (Should be cached/stored from previous step, or extract now)
        # We need the youtube_id to proceed. Extract 'v' param or similar from URL 
        # OR re-extract info if not found? 
        # A robust way is to just call extract_info again or parse ID.
        # Let's parse ID for efficiency if possible, but we need the Duration to validate timestamps.
        # So calling get_video_info is safest to ensure we have the record.
        try:
             video_data = YouTubeExtractor.get_video_info(youtube_url)
             youtube_id = video_data['youtube_id']
             duration = video_data['duration']
             available_formats = video_data['formats']
        except Exception:
             return Response({"error": "Could not retrieve video info"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validate Timestamps
        valid_time, start, end = DownloadValidator.validate_timestamps(start_time, end_time, duration)
        if not valid_time:
            # start is error message in this case
            return Response({"error": str(start)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validate Quality
        if not DownloadValidator.validate_quality(quality, available_formats):
             return Response({"error": "Invalid quality selected"}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Estimate Size (Optional check)
        estimated_size = ProgressTracker.estimate_size(
            VideoInfo.objects.get(youtube_id=youtube_id), 
            start, 
            end, 
            quality
        )
        if estimated_size > settings.YOUTUBE_DOWNLOADER_SETTINGS.get('MAX_SEGMENT_SIZE', 1073741824):
             return Response({"error": "Estimated file size too large"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 5. Create Task
        try:
            task = SegmentDownloader.create_download_task(youtube_id, start, end, quality)
            
            # 6. Queue Celery Task
            process_download_segment.delay(task.task_id)
            
            return Response({
                "task_id": task.task_id,
                "status": "pending",
                "estimated_size": estimated_size,
                "estimated_duration": end - start
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskStatusView(APIView):
    """
    GET /api/task-status/{task_id}/
    Check status of download task
    """
    def get(self, request, task_id):
        try:
            task = DownloadTask.objects.get(task_id=task_id)
            # Refresh from DB to get latest progress updates
            task.refresh_from_db()
            serializer = DownloadTaskSerializer(task)
            return Response(serializer.data)
        except DownloadTask.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
