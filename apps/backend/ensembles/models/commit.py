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

    # To create Directed Acyclic Graph DAG
    parent_commit = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    next_commit = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)


    @property
    def is_latest_commit(self) -> bool:
        return self.next_commit is None
    
    @property
    def is_initial_commit(self) -> bool:
        return self.parent_commit is None


    @property
    def mscz_file_key(self) -> str:
        return f"ensembles/{self.arrangement.ensemble.slug}/{self.arrangement.slug}/commits/{self.pk}/{self.file_name}"
    
    @property
    def mscz_file_url(self) -> str:
        """Public URL for serving to clients"""
        return default_storage.url(self.mscz_file_key)
    

    @classmethod
    def create_new_commit(cls, arrangement: Arrangement, create_kwargs: dict[str, str] = {}) -> "Commit":
        qs = cls.objects.filter(arrangement_id=arrangement.pk, next_commit__isnull=True)

        count = qs.count()

        if count == 0:
            # Creating initial commit
            new = cls.objects.create(arrangement=arrangement, **create_kwargs)

            return new

        latest_commit = qs.get() #should raise if too many
        new = cls.objects.create(arrangement=arrangement, parent=latest_commit, **create_kwargs)
        latest_commit.next_commit = new
        latest_commit.save(update_fields=["next_commit"])

        return new


