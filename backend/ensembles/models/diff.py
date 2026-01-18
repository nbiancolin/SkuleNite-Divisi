from django.db import models
from django.core.files.storage import default_storage
from ensembles.models.arrangement_version import ArrangementVersion

from logging import getLogger

logger = getLogger("app")



#TODO: Remove
class Diff(models.Model):
    from_version = models.ForeignKey(
        ArrangementVersion, on_delete=models.CASCADE, related_name="diff_as_source"
    )
    to_version = models.ForeignKey(
        ArrangementVersion, on_delete=models.CASCADE, related_name="diff_as_target"
    )

    file_name = models.CharField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    error_msg = models.CharField(blank=True, null=True)

    @property
    def from_version__str__(self):
        return self.from_version.__str__()

    @property
    def to_version__str__(self):
        return self.to_version.__str__()

    @property
    def file_key(self) -> str:
        return f"ensemble-diffs/{self.from_version.ensemble_slug}/{self.from_version.arrangement_slug}/{self.from_version.version_label}-{self.to_version.version_label}/{self.file_name}"

    @property
    def file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.file_key)

    class Meta:
        unique_together = ("from_version", "to_version")

    def __str__(self):
        return f"Diff {self.from_version} → {self.to_version}"

    def delete(self, **kwargs):
        # Delete files when diff is deleted
        keys_to_delete = [self.file_key]
        logger.warning("Deleting Diff")

        for key in keys_to_delete:
            try:
                if default_storage.exists(key):
                    default_storage.delete(key)
                    logger.info(f"Deleted file: {key}")
                else:
                    logger.warning(f"File does not exist, skipping: {key}")
            except Exception as e:
                logger.error(f"Failed to delete {key}: {e}")

        super().delete(**kwargs)