"""
On-disk layout for per-arrangement **bare** git repositories.

Directory layout (conceptual)::

    <ARRANGEMENT_GIT_ROOT>/
        arr_<arrangement_id>.git/    # bare repo (``git init --bare``)
            HEAD
            config
            objects/
            refs/
            ...

When ``ARRANGEMENT_GIT_ROOT`` is unset, repos default to
``<BASE_DIR>/arrangement_git_repos/`` (see :func:`arrangement_git_root`).
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


def arrangement_git_root() -> Path:
    """Root directory containing one bare repo directory per arrangement."""
    configured = getattr(settings, "ARRANGEMENT_GIT_ROOT", None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / "arrangement_git_repos"


def bare_repo_dirname(arrangement_id: int) -> str:
    """Bare repo directory name (not a full path), e.g. ``arr_42.git``."""
    return f"arr_{arrangement_id}.git"


def bare_repo_path_for_arrangement_id(arrangement_id: int) -> Path:
    """Absolute path to the bare repo directory for ``arrangement_id``."""
    return arrangement_git_root() / bare_repo_dirname(arrangement_id)
