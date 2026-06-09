from django.core.files.storage import default_storage
from django.db import models

from ensembles.models.utils import DeleteFilesMixin


class EnsembleTemplate(DeleteFilesMixin, models.Model):
    keys_to_delete = ["file_key"]

    is_latest = models.BooleanField(default=True)
    ensemble = models.ForeignKey("ensembles.Ensemble", on_delete=models.CASCADE, related_name="templates")
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def file_key(self):
        return f"ensembles/{self.ensemble.slug}/template.mscz"

    @property
    def file_url(self):
        return default_storage.url(self.file_key)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ensemble"],
                condition=models.Q(is_latest=True),
                name="is_latest_unique_to_ensemble",
            )
        ]

    @staticmethod
    def get_latest_for_ensemble(ensemble) -> "EnsembleTemplate | None":
        try:
            return EnsembleTemplate.objects.get(ensemble_id=ensemble.id, is_latest=True)
        except EnsembleTemplate.DoesNotExist:
            return None

    @staticmethod
    def get_all_for_ensemble(ensemble):
        return EnsembleTemplate.objects.filter(ensemble_id=ensemble.id)
