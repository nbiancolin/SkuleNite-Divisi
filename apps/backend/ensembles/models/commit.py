from django.conf import settings
from django.db import models

from ensembles.models.git_repo import GitRepo

class Commit(models.Model):
    git_repo = models.ForeignKey(
        GitRepo, related_name="commits", on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_commits",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    sha = models.CharField(max_length=40, unique=True)
    message = models.TextField()
    author_name = models.CharField(max_length=128)
    author_email = models.EmailField()
    authored_at = models.DateTimeField()
    committed_at = models.DateTimeField()
    parent_sha = models.CharField(max_length=40, blank=True, null=True)
    tag = models.CharField(max_length=64, blank=True, null=True)
    
    def __str__(self):
        tag_str = f" [{self.tag}]" if self.tag else ""
        return f"{self.sha[:7]}: {self.message.splitlines()[0]} (by {self.author_name}){tag_str}"

    class Meta:
        verbose_name = "Commit"
        verbose_name_plural = "Commits"
        ordering = ["-authored_at"]