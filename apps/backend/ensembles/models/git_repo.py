from django.db import models

import os

from ensembles.models.arrangement import Arrangement

import subprocess


class GitRepo(models.Model):
    arrangement = models.ForeignKey(
        Arrangement, related_name="git_repos", on_delete=models.CASCADE
    )
    repo_path = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Git repo for {self.arrangement} at {self.repo_path}"

    class Meta:
        verbose_name = "Git Repo"
        verbose_name_plural = "Git Repos"

    def create_bare_repo(self):
        """
        Create a bare git repository on disk at the specified path.
        """
        if not os.path.exists(self.repo_path):
            os.makedirs(self.repo_path, exist_ok=True)
            
            subprocess.run(['git', 'init', '--bare', self.repo_path], check=True)

    def save(self, *args, **kwargs):
        """
        Override save to create a bare repo on disk when the model is created.
        """
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            self.create_bare_repo()