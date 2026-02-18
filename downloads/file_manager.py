import os
import shutil
from django.conf import settings
from pathlib import Path

class FileManager:
    """Handle all file operations"""
    
    TEMP_DIR = settings.MEDIA_ROOT / 'temp'
    DOWNLOAD_DIR = settings.MEDIA_ROOT / 'downloads'
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.DOWNLOAD_DIR, exist_ok=True)
    
    @classmethod
    def get_temp_path(cls, youtube_id, quality):
        """Generate unique temp file path"""
        cls.ensure_directories()
        return cls.TEMP_DIR / f"{youtube_id}_{quality}.mp4"
    
    @classmethod
    def get_output_filename(cls, youtube_id, start, end, quality):
        """Generate output filename for segment"""
        # Format: youtubeID_startTime_endTime.mp4
        return f"{youtube_id}_{start}_{end}.mp4"
        
    @classmethod
    def get_output_path(cls, filename):
        cls.ensure_directories()
        return cls.DOWNLOAD_DIR / filename
    
    @staticmethod
    def get_file_size(file_path):
        """Return file size in bytes"""
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    
    @staticmethod
    def delete_file(file_path):
        """Safely delete file"""
        if file_path and os.path.exists(file_path):
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            except OSError:
                pass

    @classmethod
    def cleanup_old_temp_files(cls, max_age_seconds=86400):
        """Cleanup files in TEMP_DIR older than max_age_seconds"""
        import time
        now = time.time()
        cls.ensure_directories()
        
        for filename in os.listdir(cls.TEMP_DIR):
            file_path = os.path.join(cls.TEMP_DIR, filename)
            if os.stat(file_path).st_mtime < now - max_age_seconds:
                cls.delete_file(file_path)
