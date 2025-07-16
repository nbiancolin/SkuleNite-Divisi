from rest_framework import serializers
from .models import UploadSession, ProcessedFile

STYLE_CHOICES = [
    ("jazz", "Jazz"),
    ("broadway", "Broadway"),
    ("classical", 'Classical')
]

class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSession
        fields = ['id', 'created_at', 'completed']


class UploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class FormatMsczFileSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    style = serializers.ChoiceField(choices=STYLE_CHOICES)
    show_title = serializers.CharField(required=False, default=None)
    show_number = serializers.CharField(required=False, default=None)
    measures_per_line = serializers.IntegerField(required=False, default=None)
