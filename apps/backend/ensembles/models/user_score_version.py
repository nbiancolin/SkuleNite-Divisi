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

    @classmethod
    def record_for_user(cls, user, arrangement: Arrangement, commit: Commit) -> "UserScoreVersion":
        """Record which commit the user last downloaded or uploaded for this arrangement."""
        usv, _ = cls.objects.update_or_create(
            user=user,
            arrangement=arrangement,
            defaults={"commit": commit},
        )
        return usv
    
    @classmethod
    def user_is_up_to_date(cls, user, arrangement) -> bool:
        try:
            usv = cls.objects.get(user=user, arrangement=arrangement)
            uc = usv.commit
            hc = Commit.latest_for_arrangement(arrangement)

            return uc.id == hc.id

        except cls.DoesNotExist:
            # Shoud never be in this case...
            return True
