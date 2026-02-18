import uuid
from django.db import models
from videos.models import VideoInfo

class DownloadTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    video = models.ForeignKey(VideoInfo, on_delete=models.CASCADE, related_name='download_tasks')
    start_time = models.IntegerField(help_text="Start time in seconds")
    end_time = models.IntegerField(help_text="End time in seconds")
    quality = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)
    output_file = models.FileField(upload_to='downloads/', blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.video.title} ({self.start_time}-{self.end_time})"
