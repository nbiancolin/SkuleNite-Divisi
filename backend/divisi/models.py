from django.db import models
from django.utils import timezone

import uuid


class UploadSession(models.Model):
    """
    User's file upload and resulting files
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    @property
    def mscz_file_path(self) -> str:
        return f"blob/uploads/{self.id}"

    @property
    def output_file_path(self) -> str:
        return f"blob/processed/{self.id}"


class ProcessedFile(models.Model):
    session = models.ForeignKey(
        UploadSession, on_delete=models.CASCADE, related_name="files"
    )
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="processed/")
    is_score = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
