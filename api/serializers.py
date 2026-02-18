from rest_framework import serializers
from videos.models import VideoInfo
from downloads.models import DownloadTask

class VideoFormatSerializer(serializers.Serializer):
    format_id = serializers.CharField()
    quality = serializers.CharField()
    ext = serializers.CharField()
    filesize = serializers.IntegerField(allow_null=True)
    has_video = serializers.BooleanField()
    has_audio = serializers.BooleanField()

class VideoInfoSerializer(serializers.ModelSerializer):
    formats = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoInfo
        fields = ['youtube_id', 'title', 'duration', 'thumbnail_url', 'uploader', 'formats']
        
    def get_formats(self, obj):
        # available_qualities is already JSON
        return obj.available_qualities

class DownloadTaskSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadTask
        fields = ['task_id', 'status', 'progress', 'download_url', 'error_message', 'file_size']
        
    def get_download_url(self, obj):
        if obj.status == 'completed' and obj.output_file:
            return obj.output_file.url
        return None
        
    def get_file_size(self, obj):
        if obj.status == 'completed' and obj.output_file:
            try:
                return obj.output_file.size
            except:
                return None
        return None

class DownloadRequestSerializer(serializers.Serializer):
    youtube_url = serializers.URLField()
    start_time = serializers.IntegerField(min_value=0)
    end_time = serializers.IntegerField(min_value=0)
    quality = serializers.CharField()
    
    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be greater than start time.")
        return data

class ExtractInfoRequestSerializer(serializers.Serializer):
    youtube_url = serializers.URLField()
