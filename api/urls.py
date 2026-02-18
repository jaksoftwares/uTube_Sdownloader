from django.urls import path
from .views import VideoInfoView, DownloadSegmentView, TaskStatusView

urlpatterns = [
    path('extract-info/', VideoInfoView.as_view(), name='extract_info'),
    path('download-segment/', DownloadSegmentView.as_view(), name='download_segment'),
    path('task-status/<uuid:task_id>/', TaskStatusView.as_view(), name='task_status'),
]
