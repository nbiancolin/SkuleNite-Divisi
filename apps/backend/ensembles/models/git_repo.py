from django.db import models

from ensembles.models.arrangement import Arrangement


class GitRepo(models.Model):
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
        from ensembles.services.arrangement_git import remove_repo_files

        remove_repo_files(self.repo_path)

    # TODO[eventually]: Move some of the git functionality to this repo model
