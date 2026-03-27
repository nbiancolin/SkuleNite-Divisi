from django.db import models
from django.core.files.storage import default_storage

from ensembles.models.arrangement import Arrangement


class Commit(models.Model):
    """
    A commit is a working copy of an arrangement

    Whereas a Version would be considered a "release", commits are just working copies
    """

    arrangement = models.ForeignKey(
        Arrangement, related_name="commits", on_delete=models.CASCADE
    )

    file_name = models.CharField(max_length=128)
    commit_message = models.CharField(max_length=128)
    timestamp = models.DateTimeField(auto_now_add=True)

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
        cls, arrangement: Arrangement, create_kwargs: dict[str, str] | None = None
    ) -> "Commit":
        if create_kwargs is None:
            create_kwargs = {}

        latest_commit = (
            cls.objects.filter(arrangement=arrangement)
            .filter(children__isnull=True)
            .first()
        )

        if latest_commit is None:
            return cls.objects.create(arrangement=arrangement, **create_kwargs)

        return cls.objects.create(
            arrangement=arrangement, parent_commit=latest_commit, **create_kwargs
        )
