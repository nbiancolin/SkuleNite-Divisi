from rest_framework import serializers
from .models import UploadSession, ProcessedFile

STYLE_CHOICES = [
    ("jazz", "Jazz"),
    ("broadway", "Broadway"),
]

class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSession
        fields = ['id', 'created_at', 'completed']


class UploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class FormatMsczFileSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    style = serializers.ChoiceField(choices=STYLE_CHOICES)
    show_title = serializers.CharField()
    show_number = serializers.CharField()