from django.contrib import admin
from .models import VideoInfo

@admin.register(VideoInfo)
class VideoInfoAdmin(admin.ModelAdmin):
    list_display = ('youtube_id', 'title', 'duration', 'uploader')
    search_fields = ('title', 'youtube_id', 'uploader')
    list_filter = ('duration',)
