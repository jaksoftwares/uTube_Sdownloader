from django.contrib import admin
from .models import DownloadTask

@admin.register(DownloadTask)
class DownloadTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'video', 'start_time', 'end_time', 'quality', 'status', 'progress', 'created_at')
    list_filter = ('status', 'quality')
    search_fields = ('task_id', 'video__title')
    readonly_fields = ('task_id', 'created_at', 'completed_at')
