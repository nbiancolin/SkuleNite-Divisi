from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ensembles.git.exceptions import ArrangementGitError
from ensembles.git.paths import arrangement_git_root, bare_repo_path_for_arrangement_id
from ensembles.git.runner import run_git
from ensembles.models import Arrangement
from ensembles.models.commit import Commit
from ensembles.models.git_repo import GitRepo


def remove_repo_files(repo_path: str) -> None:
    """
    Best-effort removal of on-disk repo data for a deleted :class:`~ensembles.models.GitRepo` row.
    Only deletes paths that resolve under :func:`~ensembles.git.paths.arrangement_git_root`.
    """
    root = arrangement_git_root().resolve()
    path = Path(repo_path).expanduser()
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def init_repo(arrangement: Arrangement) -> str:
    """
    Ensure a per-arrangement bare git repo exists on disk and is referenced by
    :class:`~ensembles.models.GitRepo` (one row per :class:`~ensembles.models.Arrangement`).
    """
    if arrangement.pk is None:
        raise ArrangementGitError("Arrangement must be saved before initializing a repo.")

    root = arrangement_git_root()
    root.mkdir(parents=True, exist_ok=True)

    repo_row = GitRepo.objects.filter(arrangement=arrangement).order_by("id").first()
    if repo_row is None:
        repo_path = str(bare_repo_path_for_arrangement_id(arrangement.id))
        repo_row = GitRepo.objects.create(arrangement=arrangement, repo_path=repo_path)
    else:
        repo_path = repo_row.repo_path

    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        repo_dir.mkdir(parents=True, exist_ok=True)

    if not (repo_dir / "HEAD").exists():
        try:
            run_git(["init", "--bare", "--initial-branch=main", str(repo_dir)])
        except ArrangementGitError:
            run_git(["init", "--bare", str(repo_dir)])

    driver_cmd = "python -m ensembles.services.scoreforge_merge_driver %O %A %B"
    run_git(["--git-dir", str(repo_dir), "config", "merge.scoreforge.name", "ScoreForge canonical merge"])
    run_git(["--git-dir", str(repo_dir), "config", "merge.scoreforge.driver", driver_cmd])

    default_branch = "main"
    run_git(["--git-dir", str(repo_dir), "symbolic-ref", "HEAD", f"refs/heads/{default_branch}"])

    return repo_path


def tag_version(arrangement: Arrangement, sha: str, tag: str) -> None:
    """Create or move a git tag ``tag`` to ``sha`` in the arrangement's bare repo."""
    repo_path = Path(init_repo(arrangement))
    run_git(["--git-dir", str(repo_path), "tag", "-f", tag, sha])
