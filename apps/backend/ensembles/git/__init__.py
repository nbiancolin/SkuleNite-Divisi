"""
Arrangement git: one **bare** repository per :class:`~ensembles.models.Arrangement`.

See :mod:`ensembles.git.paths` for the on-disk directory layout.
"""

from ensembles.git.exceptions import ArrangementGitError
from ensembles.git.materialize import materialize_commit_mscz_to_version
from ensembles.git.repo import init_repo, remove_repo_files, tag_version
from ensembles.git.runner import run_git
from ensembles.git.snapshots import GitAuthor, commit_canonical_snapshot

__all__ = [
    "ArrangementGitError",
    "GitAuthor",
    "commit_canonical_snapshot",
    "init_repo",
    "materialize_commit_mscz_to_version",
    "remove_repo_files",
    "run_git",
    "tag_version",
]
