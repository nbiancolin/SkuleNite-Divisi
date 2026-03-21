from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.utils import timezone

from ensembles.git.exceptions import ArrangementGitError
from ensembles.git.repo import init_repo
from ensembles.git.runner import run_git
from ensembles.models import Arrangement
from ensembles.models.commit import Commit
from ensembles.models.git_repo import GitRepo


@dataclass(frozen=True)
class GitAuthor:
    name: str
    email: str


def commit_canonical_snapshot(
    arrangement: Arrangement,
    payload_dir: Path,
    *,
    author: GitAuthor,
    timestamp: datetime | None = None,
    message: str,
    created_by=None,
) -> Commit:
    """
    Create a commit in the arrangement's bare repo containing the ``payload_dir`` tree.
    Returns the persisted :class:`~ensembles.models.Commit` row.
    """
    repo_path = Path(init_repo(arrangement))
    default_branch = "main"
    git_repo = GitRepo.objects.filter(arrangement=arrangement, repo_path=str(repo_path)).order_by("id").first()
    if git_repo is None:
        raise ArrangementGitError(
            f"Could not find GitRepo row for arrangement {arrangement.id} at {repo_path}"
        )

    with tempfile.TemporaryDirectory(prefix="arr_git_work_") as tmp:
        tmp_dir = Path(tmp)
        workdir = tmp_dir / "work"

        run_git(["clone", str(repo_path), str(workdir)])

        try:
            run_git(["checkout", default_branch], cwd=workdir)
        except ArrangementGitError:
            run_git(["checkout", "-b", default_branch], cwd=workdir)

        for src in payload_dir.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(payload_dir)
            dest = workdir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())

        run_git(["add", "-A"], cwd=workdir)
        status_porcelain = run_git(["status", "--porcelain"], cwd=workdir)

        if not status_porcelain.strip():
            sha = run_git(["rev-parse", "HEAD"], cwd=workdir)
            existing = Commit.objects.filter(git_repo=git_repo, sha=sha).first()
            if existing is not None:
                return existing
            raise ArrangementGitError(
                "No changes detected in canonical snapshot and no existing Commit row found for HEAD."
            )

        env: dict[str, str] = {}
        if timestamp is not None:
            iso = timestamp.isoformat()
            env["GIT_AUTHOR_DATE"] = iso
            env["GIT_COMMITTER_DATE"] = iso

        run_git(
            [
                "-c",
                "user.name=Divisi",
                "-c",
                "user.email=divisi@local",
                "commit",
                "-m",
                message,
                "--author",
                f"{author.name} <{author.email}>",
            ],
            cwd=workdir,
            env=env,
        )

        sha = run_git(["rev-parse", "HEAD"], cwd=workdir)
        parent_sha = run_git(["rev-parse", "HEAD^"], cwd=workdir) if _has_parent(workdir) else None

        run_git(["push", "origin", default_branch], cwd=workdir)

    authored_at = timestamp or timezone.now()
    committed_at = timestamp or timezone.now()

    return Commit.objects.create(
        git_repo=git_repo,
        created_by=created_by,
        sha=sha,
        message=message,
        author_name=author.name,
        author_email=author.email,
        authored_at=authored_at,
        committed_at=committed_at,
        parent_sha=parent_sha,
    )


def _has_parent(workdir: Path) -> bool:
    try:
        run_git(["rev-parse", "HEAD^"], cwd=workdir)
        return True
    except ArrangementGitError:
        return False
