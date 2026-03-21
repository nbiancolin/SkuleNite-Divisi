from django.db import models

from ensembles.models.arrangement import Arrangement


class GitRepo(models.Model):
    """
    One **bare** git repository on disk per :class:`~ensembles.models.Arrangement`.

    Relationships:

    * ``Arrangement`` ←1:1→ ``GitRepo`` (this model): ``arrangement.git_repo``
    * ``GitRepo`` ←1:N→ :class:`~ensembles.models.Commit`: ``git_repo.commits``

    The filesystem path is stored in ``repo_path`` (see ``ensembles.git.paths``).
    """

    arrangement = models.OneToOneField(
        Arrangement, related_name="git_repo", on_delete=models.CASCADE
    )
    repo_path = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Git repo for {self.arrangement} at {self.repo_path}"

    class Meta:
        verbose_name = "Git Repo"
        verbose_name_plural = "Git Repos"

    def remove_files_from_disk(self) -> None:
        from ensembles.git.repo import remove_repo_files

        remove_repo_files(self.repo_path)
