from celery import shared_task
from django.utils import timezone
from .models import DownloadTask
from .services import SegmentDownloader
from .file_manager import FileManager
from videos.models import VideoInfo
import logging
import os

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_download_segment(self, task_id):
    """
    Background task to:
    1. Get DownloadTask instance
    2. Update status to 'processing'
    3. Download full video to temp location
    4. Extract specified segment using ffmpeg
    5. Save segment to media/downloads/
    6. Update task status to 'completed'
    
    Handle failures with proper error messages
    Update progress periodically (0-100%)
    """
    from django.db import transaction
    
    try:
        task = DownloadTask.objects.get(task_id=task_id)
    except DownloadTask.DoesNotExist:
        logger.error(f"Task {task_id} not found")
        return "Task not found"

    # Progress callback for yt-dlp
    def update_progress(percent):
        try:
            with transaction.atomic():
                task.progress = percent
                task.save(update_fields=['progress'])
        except Exception as e:
            logger.error(f"Progress update error: {e}")

    try:
        # 2. Update status to 'processing'
        with transaction.atomic():
            task.status = 'processing'
            task.progress = 5
            task.save(update_fields=['status', 'progress'])
        
        # Validate Video Info exists
        if not task.video:
             raise ValueError("Associated video info missing")

        # 3. Download full video to temp location
        # Generate temp path
        temp_path = FileManager.get_temp_path(task.video.youtube_id, task.quality)
        
        # Check if we already have the full video in temp (caching optimization)
        if not os.path.exists(temp_path):
            # Update progress - starting download
            with transaction.atomic():
                task.progress = 10
                task.save(update_fields=['progress'])
            
            # Download with progress callback
            SegmentDownloader.download_full_video(
                task.video.youtube_id, 
                task.quality, 
                temp_path,
                progress_callback=update_progress
            )
        else:
            # Use cached file
            update_progress(65)
        
        # Update progress - download complete, starting extraction
        with transaction.atomic():
            task.progress = 70
            task.save(update_fields=['progress'])
        
        # 4. Extract specified segment
        output_filename = FileManager.get_output_filename(
            task.video.youtube_id, 
            task.start_time, 
            task.end_time, 
            task.quality
        )
        output_path = FileManager.get_output_path(output_filename)
        
        SegmentDownloader.extract_segment(
            temp_path, 
            task.start_time, 
            task.end_time, 
            output_path
        )
        
        # Update progress - extraction complete, saving file
        with transaction.atomic():
            task.progress = 90
            task.save(update_fields=['progress'])
        
        # 5. Save segment to media/downloads/ (Update database record)
        # The file is already at output_path, we just need to link it
        # Relative path for FileField
        relative_path = f"downloads/{output_filename}"
        
        # 6. Update task status to 'completed'
        with transaction.atomic():
            task.status = 'completed'
            task.progress = 100
            task.completed_at = timezone.now()
            task.output_file = relative_path
            task.save()
        
        return "Completed"

    except Exception as e:
        with transaction.atomic():
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
        logger.error(f"Download task {task_id} failed: {e}")
        return f"Failed: {e}"

@shared_task
def cleanup_old_files():
    """Daily task to remove files older than 24 hours"""
    FileManager.cleanup_old_temp_files(max_age_seconds=86400)
    return "Cleanup completed"
