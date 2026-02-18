import os
import uuid
import logging
from django.conf import settings
from .models import DownloadTask
from .file_manager import FileManager
from videos.models import VideoInfo
import yt_dlp
import imageio_ffmpeg

logger = logging.getLogger(__name__)

class SegmentDownloader:
    """Handle segment extraction and downloading"""
    
    @staticmethod
    def create_download_task(youtube_id, start_time, end_time, quality):
        """
        - Validate timestamps (0 <= start < end <= duration)
        - Create DownloadTask record
        - Queue Celery task for processing
        - Return task_id for tracking
        """
        try:
            video = VideoInfo.objects.get(youtube_id=youtube_id)
        except VideoInfo.DoesNotExist:
            raise ValueError("Video info not found. Please extract info first.")

        # Basic validation (detailed validation should happen in API/Validator before calling this)
        if start_time < 0 or end_time > video.duration or start_time >= end_time:
             raise ValueError("Invalid timestamps")

        task = DownloadTask.objects.create(
            video=video,
            start_time=start_time,
            end_time=end_time,
            quality=quality,
            status='pending'
        )
        
        # We will return the task object, the caller (View) will handle queuing the Celery task
        # to keep service logic slightly decoupled from async execution definition if needed,
        # or we can queue it here. 
        # Given the prompt structure "Queue Celery task for processing", I will likely
        # trigger it in the View to get the task ID back immediately, or import the task here.
        # To avoid circular imports (tasks importing services, services importing tasks), 
        # it's often better to return the task and let the controller/view trigger the async job.
        
        return task
    
    @staticmethod
    def download_full_video(youtube_id, quality, temp_path, progress_callback=None):
        """Download complete video file to temp storage"""
        # We need to construct the URL or use yt-dlp to download to temp_path
        # format_id is passed as 'quality' usually in this context based on previous files
        
        url = f"https://www.youtube.com/watch?v={youtube_id}"
        
        # Construct proper format selector from quality string (e.g., '720p')
        if quality == 'best':
            format_selector = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        elif quality.endswith('p') and quality[:-1].isdigit():
            height = quality[:-1]
            # Select best video with height <= requested height (ensures we get the closest match)
            format_selector = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}][ext=mp4]/best[height<={height}]'
        else:
            # Fallback or if it's a specific format_id
            format_selector = quality

        # Progress hook to update progress
        def progress_hook(d):
            if d['status'] == 'downloading':
                if progress_callback:
                    # Calculate percentage based on downloaded bytes
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = int((downloaded / total) * 60)  # Max 60% for download phase
                        progress_callback(percent)
            elif d['status'] == 'finished':
                if progress_callback:
                    progress_callback(65)  # Download complete

        ydl_opts = {
            'format': format_selector,
            'outtmpl': str(temp_path),
            'quiet': True,
            'overwrites': True,
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
            'progress_hooks': [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return temp_path
    
    @staticmethod
    def extract_segment(input_path, start_time, end_time, output_path):
        """Use ffmpeg to extract specific segment"""
        import subprocess
        
        try:
            # Get FFmpeg path using imageio_ffmpeg (consistent with download method)
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            # Use ffmpeg directly via subprocess for more reliable segment extraction
            # This avoids dependency issues with moviepy's wrapper functions
            ffmpeg_cmd = [
                ffmpeg_path,
                '-y',  # Overwrite output file without asking
                '-i', str(input_path),
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c', 'copy',  # Copy streams without re-encoding for speed
                '-avoid_negative_ts', 'make_zero',
                str(output_path)
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error extracting segment: {e.stderr}")
            raise Exception(f"FFmpeg error: {e.stderr}")
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install ffmpeg.")
            raise Exception("FFmpeg not found. Please install ffmpeg.")
    
    @staticmethod
    def cleanup_temp_files(file_path):
        """Remove temporary files after processing"""
        FileManager.delete_file(file_path)
