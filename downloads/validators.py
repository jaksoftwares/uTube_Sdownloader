import re

class DownloadValidator:
    """Validate all inputs before processing"""
    
    YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    
    @classmethod
    def validate_youtube_url(cls, url):
        """Check if URL is valid YouTube URL"""
        if not re.match(cls.YOUTUBE_REGEX, url):
            return False
        return True
    
    @staticmethod
    def validate_timestamps(start, end, duration):
        """
        - start >= 0
        - end > start
        - end <= duration
        """
        try:
            start = int(start)
            end = int(end)
            duration = int(duration)
            
            if start < 0:
                raise ValueError("Start time cannot be negative")
            if end <= start:
                raise ValueError("End time must be greater than start time")
            if end > duration:
                # Allow a small buffer for drift/imprecision in duration
                if end > duration + 5:
                    raise ValueError("End time exceeds video duration")
                end = duration
            
            return True, start, end
        except ValueError as e:
            return False, str(e), None

    @staticmethod
    def validate_quality(quality, available_formats):
        """Check if requested quality is available"""
        # available_formats is likely a list of dicts [{'format_id': '...', 'quality': '720p', ...}]
        # This checks if the requested quality exists in available formats
        valid_qualities = [fmt.get('quality') for fmt in available_formats]
        if quality not in valid_qualities:
             # Also allow passing format_id directly
             valid_ids = [fmt.get('format_id') for fmt in available_formats]
             if quality in valid_ids:
                 return True
             return False
        return True
    
    @staticmethod
    def validate_file_size(estimated_size):
        """Check if segment size is within limits (e.g., < 10GB)"""
        if estimated_size > 1024 * 1024 * 1024 * 10:
            return False, "File size exceeds 10GB limit"
        return True, None
