from django.test import TestCase
from unittest.mock import patch, MagicMock
from .models import DownloadTask
from videos.models import VideoInfo
from .services import SegmentDownloader
from .validators import DownloadValidator
from .tasks import process_download_segment

class DownloadValidatorTests(TestCase):
    def test_validate_youtube_url(self):
        valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        invalid_url = "https://example.com/video"
        
        self.assertTrue(DownloadValidator.validate_youtube_url(valid_url))
        self.assertFalse(DownloadValidator.validate_youtube_url(invalid_url))

    def test_validate_timestamps(self):
        duration = 1000
        # Valid
        valid, start, end = DownloadValidator.validate_timestamps(10, 20, duration)
        self.assertTrue(valid)
        self.assertEqual(start, 10)
        self.assertEqual(end, 20)
        
        # Invalid start
        valid, msg, _ = DownloadValidator.validate_timestamps(-1, 20, duration)
        self.assertFalse(valid)
        
        # Invalid end
        valid, msg, _ = DownloadValidator.validate_timestamps(10, 5, duration)
        self.assertFalse(valid)
        
        # Exceeds duration significantly
        valid, msg, end = DownloadValidator.validate_timestamps(10, 2000, duration)
        self.assertFalse(valid)
        
        # Exceeds duration slightly (drift)
        valid, start, end = DownloadValidator.validate_timestamps(10, 1003, duration)
        self.assertTrue(valid)
        self.assertEqual(end, duration)
        
        # Exceeds max segment (3600s)
        valid, msg, _ = DownloadValidator.validate_timestamps(0, 3601, 5000)
        self.assertFalse(valid)

class SegmentDownloaderTests(TestCase):
    def setUp(self):
        self.video = VideoInfo.objects.create(
            youtube_id="test_id",
            title="Test Video",
            duration=300
        )

    def test_create_download_task(self):
        task = SegmentDownloader.create_download_task(
            youtube_id="test_id",
            start_time=10,
            end_time=20,
            quality="720p"
        )
        self.assertIsNotNone(task.task_id)
        self.assertEqual(task.status, 'pending')

    @patch('downloads.services.yt_dlp.YoutubeDL')
    def test_download_full_video(self, mock_ydl):
        # Mock context manager
        mock_instance = MagicMock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        
        path = SegmentDownloader.download_full_video("test_id", "720p", "temp/path.mp4")
        self.assertEqual(path, "temp/path.mp4")
        mock_instance.download.assert_called_once()

    @patch('downloads.services.ffmpeg_extract_subclip')
    def test_extract_segment(self, mock_ffmpeg):
        SegmentDownloader.extract_segment("input.mp4", 10, 20, "output.mp4")
        mock_ffmpeg.assert_called_with("input.mp4", 10, 20, targetname="output.mp4")

class CeleryTaskTests(TestCase):
    def setUp(self):
        self.video = VideoInfo.objects.create(
            youtube_id="test_id",
            title="Test Video",
            duration=300
        )
        self.task = DownloadTask.objects.create(
            video=self.video,
            start_time=10,
            end_time=20,
            quality="720p",
            status='pending'
        )

    @patch('downloads.tasks.SegmentDownloader')
    @patch('downloads.tasks.FileManager') 
    def test_process_download_segment_success(self, MockFileManager, MockDownloader):
        # Setup mocks
        MockFileManager.get_temp_path.return_value = "temp.mp4"
        MockFileManager.get_output_filename.return_value = "out.mp4"
        MockFileManager.get_output_path.return_value = "media/downloads/out.mp4"
        
        # Call task synchronously
        result = process_download_segment(self.task.task_id)
        
        self.assertEqual(result, "Completed")
        
        # Refresh task from DB
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'completed')
        self.assertEqual(self.task.progress, 100)
