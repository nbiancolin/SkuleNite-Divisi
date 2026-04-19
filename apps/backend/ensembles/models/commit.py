from django.db import models
from django.core.files.storage import default_storage

from ensembles.models import Arrangement, ArrangementVersion
from django.conf import settings


class Commit(models.Model):
    """
    A commit is a working copy of an arrangement

    Whereas a Version would be considered a "release", commits are just working copies
    """

    arrangement = models.ForeignKey(
        Arrangement, related_name="commits", on_delete=models.CASCADE
    )

    #TODO: eventually cleanup blank/null on this
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="commits", on_delete=models.PROTECT, blank=True, null=True
    )

    file_name = models.CharField(max_length=128)
    message = models.CharField(max_length=128)
    timestamp = models.DateTimeField(auto_now_add=True)

    version = models.ForeignKey(ArrangementVersion, on_delete=models.SET_NULL, blank=True, null=True, related_name="commit")

    @property
    def has_version(self) -> bool:
        return self.version is not None

    parent_commit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="children",
    )

    @property
    def is_latest_commit(self) -> bool:
        return not self.children.exists()

    @property
    def is_initial_commit(self) -> bool:
        return self.parent_commit is None

    @property
    def mscz_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/commits/{self.pk}/{self.file_name}"

    @property
    def mscz_file_url(self) -> str:
        return default_storage.url(self.mscz_file_key)

    @classmethod
    def create_new_commit(
        cls, arrangement: Arrangement, created_by_user, create_kwargs: dict[str, str] | None = None
    ) -> "Commit":
        if create_kwargs is None:
            create_kwargs = {}

        latest_commit = (
            cls.objects.filter(arrangement=arrangement)
            .filter(children__isnull=True)
            .first()
        )

        if latest_commit is None:
            return cls.objects.create(arrangement=arrangement, created_by=created_by_user, **create_kwargs)

        return cls.objects.create(
            arrangement=arrangement,
            parent_commit=latest_commit,
            created_by=created_by_user,
            **create_kwargs,
        )

    @classmethod
    def latest_for_arrangement(cls, arrangement: Arrangement) -> "Commit | None":
        """Tip commit for this arrangement (no child commits), or None if empty."""
        return (
            cls.objects.filter(arrangement=arrangement, children__isnull=True)
            .order_by("-id")
            .first()
        )
