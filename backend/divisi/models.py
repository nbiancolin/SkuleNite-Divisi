from django.db import models
from django.utils import timezone

import os
import shutil
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
    def mscz_file_location(self) -> str:
        return f"blob/uploads/{self.id}"

    @property
    def mscz_file_path(self) -> str:
        return f"blob/uploads/{self.id}/{self.file_name}"

    @property
    def output_file_location(self) -> str:
        return f"blob/processed/{self.id}"

    @property
    def output_file_path(self) -> str:
        return f"blob/processed/{self.id}/{self.file_name}"
    
    def delete(self, **kwargs):
        #delete files when session is deleted
        paths_to_delete = [self.mscz_file_location, self.output_file_location]

        for rel_path in paths_to_delete:
            abs_path = os.path.abspath(rel_path) 

            if os.path.exists(abs_path):
                try:
                    shutil.rmtree(abs_path)
                    logger.info(f"Deleted folder: {abs_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {abs_path}: {e}")
            else:
                logger.warning(f"Path does not exist, skipping: {abs_path}")

        super().delete(**kwargs)


class ProcessedFile(models.Model):
    session = models.ForeignKey(
        UploadSession, on_delete=models.CASCADE, related_name="files"
    )
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="processed/")
    is_score = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
