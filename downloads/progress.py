from downloads.models import DownloadTask

class ProgressTracker:
    """Track and update download progress"""
    
    @staticmethod
    def update_progress(task_id, percent):
        """Update DownloadTask progress field"""
        try:
            task = DownloadTask.objects.get(task_id=task_id)
            task.progress = min(max(percent, 0), 100)
            task.save()
        except DownloadTask.DoesNotExist:
            pass

    @staticmethod
    def get_progress(task_id):
        """Return current progress"""
        try:
            task = DownloadTask.objects.get(task_id=task_id)
            return task.progress
        except DownloadTask.DoesNotExist:
            return 0
    
    @staticmethod
    def estimate_size(video_info, start, end, quality):
        """Calculate estimated file size based on format bitrate/duration"""
        # video_info is VideoInfo object or dict
        # Available from model: available_qualities is JSON
        
        qualities = video_info.available_qualities
        target_format = None
        
        # Try to find format by quality label
        for fmt in qualities:
            if fmt.get('quality') == quality or fmt.get('format_id') == quality:
                target_format = fmt
                break
        
        if not target_format:
            return 0
            
        full_size = target_format.get('filesize')
        full_duration = video_info.duration
        
        if not full_size or not full_duration:
            return 0
            
        duration = end - start
        estimated_size = (full_size / full_duration) * duration
        return int(estimated_size)
