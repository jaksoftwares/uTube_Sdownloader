from django.db import models

class VideoInfo(models.Model):
    youtube_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    duration = models.IntegerField(help_text="Duration in seconds")
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    uploader = models.CharField(max_length=255, blank=True, null=True)
    available_qualities = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
