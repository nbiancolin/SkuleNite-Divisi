from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ensembles.models import Arrangement, GitRepo
from ensembles.services.arrangement_git import init_repo
from logging import getLogger

logger = getLogger("arrangement_git")


@receiver(post_save, sender=Arrangement)
def ensure_arrangement_git_repo(sender, instance: Arrangement, created: bool, **kwargs):
    if not created:
        return
    # Best-effort: repo creation should not block arrangement creation.
    try:
        init_repo(instance)
    except Exception as e:
        # Some environments (CI/dev without git) may not have git available.
        logger.warning("Failed to init repo for arrangement %s: %s", instance.id, e)


@receiver(post_delete, sender=GitRepo)
def remove_git_repo_files(sender, instance: GitRepo, **kwargs):
    instance.remove_files_from_disk()
