from django.db import models
from django.core.files.storage import default_storage

import os
from logging import getLogger

from ensembles.models.arrangement import Arrangement

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ensembles.models.part import PartAsset

logger = getLogger("app")


class _Status(models.TextChoices):
    NONE = "N", "none"
    PROCESSING = "P", "processing"
    COMPLETE = "C", "complete"
    ERROR = "E", "error"

class ArrangementVersion(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="versions", on_delete=models.CASCADE
    )

    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager
        parts: RelatedManager["PartAsset"]

    file_name = models.CharField(max_length=128)
    version_label = models.CharField(max_length=10, default="0.0.0")  # 1.0.0 or 1.2.3
    timestamp = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=False)
    
    ExportStatus = _Status
    export_state = models.CharField(max_length=1, choices=ExportStatus.choices, default=ExportStatus.NONE)

    AudioStatus = _Status
    audio_state = models.CharField(max_length=1, choices=AudioStatus.choices, default=AudioStatus.NONE)

    num_measures_per_line_score = models.IntegerField()
    num_measures_per_line_part = models.IntegerField()
    num_lines_per_page = models.IntegerField()


    @property
    def is_processing(self):
        return self.export_state == self.ExportStatus.PROCESSING
    
    @property
    def error_on_export(self):
        return self.export_state == self.ExportStatus.ERROR

    @property
    def version_label_full(self) -> str:
        """Includes the v and is not just the number"""
        return f"v{self.version_label}"

    @property
    def mscz_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/raw/{self.file_name}"

    @property
    def output_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{self.file_name}"

    @property
    def score_pdf_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext}.pdf"
    
    @property
    def audio_file_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext}.mp3"

    @property
    def score_parts_pdf_key(self) -> str:
        filename_without_ext = os.path.splitext(self.file_name)[0]
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/{self.version_label}/processed/{filename_without_ext} - Score+Parts.pdf"

    @property
    def mscz_file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.mscz_file_key)

    @property
    def output_file_url(self) -> str:
        return default_storage.url(self.output_file_key)

    @property
    def score_pdf_url(self) -> str:
        return default_storage.url(self.score_pdf_key)

    @property
    def score_parts_pdf_url(self) -> str:
        return default_storage.url(self.score_parts_pdf_key)

    @property
    def audio_file_url(self) -> str:
        return default_storage.url(self.audio_file_key)

    def _bump_version_label(self, version_type, old_version_label):
        major, minor, patch = map(int, old_version_label.split("."))
        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"

    def save(self, *args, **kwargs):
        version_type = kwargs.pop("version_type", None)

        if version_type:
            # This is a new version, and caller wants to bump the version
            latest = ArrangementVersion.objects.filter(
                arrangement=self.arrangement, is_latest=True
            ).first()

            old_label = latest.version_label if latest else "0.0.0"
            self.version_label = self._bump_version_label(version_type, old_label)

            # Mark all other versions as not latest
            ArrangementVersion.objects.filter(arrangement=self.arrangement).update(
                is_latest=False
            )

            self.is_latest = True

        super().save(*args, **kwargs)

    def delete(self, **kwargs):
        # Delete files when version is deleted
        keys_to_delete = [
            self.mscz_file_key,
            self.output_file_key,
            self.score_pdf_key,
            self.score_parts_pdf_key,
        ]
        
        # Also delete all part PDFs
        for part in self.parts.all():
            if part.file_key not in keys_to_delete:
                keys_to_delete.append(part.file_key)
        
        logger.warning("Deleting ArrangementVersion")

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

    @property
    def arrangement_title(self):
        return self.arrangement.title

    @property
    def arrangement_slug(self):
        return self.arrangement.slug

    @property
    def ensemble_name(self):
        return self.arrangement.ensemble_name

    @property
    def ensemble_slug(self):
        return self.arrangement.ensemble_slug
    
    @property
    def ensemble(self):
        return self.arrangement.ensemble

    def __str__(self):
        return f"{self.arrangement.__str__()} (v{self.version_label})"

    class Meta:
        ordering = ["-timestamp"]