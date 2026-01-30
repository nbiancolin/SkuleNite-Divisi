from __future__ import annotations

from django.db import models


class PartNameAlias(models.Model):
    """
    Persisted mapping from a "raw" incoming part label (often produced by MuseScore)
    to a canonical PartName, scoped per arrangement so re-uploading arrangement A
    uses A's alias (e.g. "Flute I" -> Flute) while arrangement B can have different
    part names.
    """

    ensemble = models.ForeignKey(
        "ensembles.Ensemble", related_name="part_name_aliases", on_delete=models.CASCADE
    )
    arrangement = models.ForeignKey(
        "ensembles.Arrangement",
        related_name="part_name_aliases",
        on_delete=models.CASCADE,
    )
    canonical_part_name = models.ForeignKey(
        "ensembles.PartName", related_name="aliases", on_delete=models.CASCADE
    )

    # What we saw / want to match against (keep original for admin/debugging)
    alias = models.CharField(max_length=64)
    # Normalized for stable lookup (case/whitespace-insensitive)
    alias_normalized = models.CharField(max_length=64)

    @staticmethod
    def normalize(value: str) -> str:
        # Lowercase and collapse whitespace.
        return " ".join((value or "").strip().lower().split())

    def save(self, *args, **kwargs):
        if not self.alias_normalized:
            self.alias_normalized = self.normalize(self.alias)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'"{self.alias}" -> {self.canonical_part_name} ({self.arrangement})'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ensemble", "arrangement", "alias_normalized"],
                name="uniq_partnamealias_ens_arr_aliasnorm",
            )
        ]

