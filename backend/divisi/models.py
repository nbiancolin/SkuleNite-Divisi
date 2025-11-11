from django.db import models
from django.core.files.storage import default_storage

import uuid

import logging

logger = logging.getLogger(__name__)


class UploadSession(models.Model):
    """
    User's file upload and resulting files
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    file_name = models.CharField()
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    @property
    def mscz_file_key(self) -> str:
        return f"part-formatter/uploads/{self.id}/{self.file_name}"

    @property
    def output_file_key(self) -> str:
        return f"part-formatter/processed/{self.id}/{self.file_name}"

    @property
    def mscz_file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.mscz_file_key)

    @property
    def output_file_url(self) -> str:
        return default_storage.url(self.output_file_key)

    def delete(self, **kwargs):
        # delete files when session is deleted
        paths_to_delete = [
            self.mscz_file_key,
            self.output_file_key,
            self.output_file_key[:-4] + "pdf",
        ]
        for path in paths_to_delete:
            default_storage.delete(path)

        super().delete(**kwargs)


# TODO[]: This model is unused ... Was initially going to be used for having the standalone pat exporter export parts,
# I dont think I will do this, but will leave it bc we dont need another migration
class ProcessedFile(models.Model):
    session = models.ForeignKey(
        UploadSession, on_delete=models.CASCADE, related_name="files"
    )
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="processed/")
    is_score = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
