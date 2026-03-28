from django.conf import settings
from django.db import models

from ensembles.models.arrangement import Arrangement
from ensembles.models.commit import Commit


class UserScoreVersion(models.Model):
    """
    Tracks which commit each user last downloaded for an arrangement (working score).
    One row per (user, arrangement); updated when the user records a download.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_score_versions",
        on_delete=models.CASCADE,
    )
    arrangement = models.ForeignKey(
        Arrangement,
        related_name="user_score_versions",
        on_delete=models.CASCADE,
    )
    commit = models.ForeignKey(
        Commit,
        related_name="user_score_versions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "arrangement")
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.user_id} @ arrangement {self.arrangement_id} -> commit {self.commit_id}"
