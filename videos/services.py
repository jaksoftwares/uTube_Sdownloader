from .models import VideoInfo
import yt_dlp
import datetime

class YouTubeExtractor:
    """Extract video info and available formats"""
    
    YDL_OPTS = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True,
        # 'quiet': True, # Disable quiet mode for debugging
        'ignoreerrors': True,
        'no_warnings': True,
        # 'logger': MyLogger(), # Could add a custom logger
    }

    @staticmethod
    def get_video_info(youtube_url):
        """
        Input: YouTube URL
        Output: {
            'youtube_id': str,
            'title': str,
            'duration': int,
            'thumbnail': str,
            'uploader': str,
            'formats': [{
                'format_id': str,
                'quality': str,
                'ext': str,
                'filesize': int,
                'has_video': bool,
                'has_audio': bool
            }]
        }
        """
        try:
            with yt_dlp.YoutubeDL(YouTubeExtractor.YDL_OPTS) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                
                youtube_id = info.get('id')
                title = info.get('title')
                duration = info.get('duration')
                thumbnail = info.get('thumbnail')
                uploader = info.get('uploader')
                
                formats_data = info.get('formats', [])
                filtered_formats = []
                
                for fmt in formats_data:
                    # Filter for MP4 and standard resolutions
                    if fmt.get('ext') != 'mp4':
                        continue
                        
                    format_id = fmt.get('format_id')
                    height = fmt.get('height')
                    if not height:
                        continue
                    
                    quality = f"{height}p"
                    filesize = fmt.get('filesize')
                    
                    # Avoid duplicates or very specific formats if not needed
                    # For simplicity, we can keep all mp4 video formats
                    filtered_formats.append({
                        'format_id': format_id,
                        'quality': quality,
                        'ext': fmt.get('ext'),
                        'filesize': filesize,
                        'has_video': fmt.get('vcodec') != 'none',
                        'has_audio': fmt.get('acodec') != 'none'
                    })

                video_data = {
                    'youtube_id': youtube_id,
                    'title': title,
                    'duration': duration,
                    'thumbnail': thumbnail,
                    'uploader': uploader,
                    'formats': filtered_formats
                }
                
                # Save or update VideoInfo
                VideoInfo.objects.update_or_create(
                    youtube_id=youtube_id,
                    defaults={
                        'title': title,
                        'duration': duration,
                        'thumbnail_url': thumbnail,
                        'uploader': uploader,
                        'available_qualities': filtered_formats
                    }
                )
                
                return video_data
                
        except Exception as e:
            # Re-raise or handle error appropriately
            raise Exception(f"Failed to extract video info: {str(e)}")

    @staticmethod
    def get_download_url(youtube_id, format_id):
        """Get direct download URL for specific format"""
        # Typically yt-dlp doesn't give a direct persistent download URL unless we extract it again.
        # But for this task, the goal is likely to get the URL to stream/download *during* processing.
        # This method might be used by the downloader service.
        url = f"https://www.youtube.com/watch?v={youtube_id}"
        with yt_dlp.YoutubeDL({'format': format_id}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url')
