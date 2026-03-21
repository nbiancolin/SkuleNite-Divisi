"""Backward-compatible imports for ``ensembles.git`` (prefer ``ensembles.git`` in new code)."""

from ensembles.git import (  # noqa: F401
    ArrangementGitError,
    GitAuthor,
    commit_canonical_snapshot,
    init_repo,
    materialize_commit_mscz_to_version,
    remove_repo_files,
    run_git,
    tag_version,
)

# Legacy name used by older call sites.
_run_git = run_git

__all__ = [
    "ArrangementGitError",
    "GitAuthor",
    "commit_canonical_snapshot",
    "init_repo",
    "materialize_commit_mscz_to_version",
    "remove_repo_files",
    "run_git",
    "tag_version",
    "_run_git",
]
