import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ensembles.models import Arrangement
from ensembles.models.commit import Commit
from ensembles.models.git_repo import GitRepo


class ArrangementGitError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitAuthor:
    name: str
    email: str


def _run_git(args: list[str], *, cwd: str | Path | None = None, env: dict[str, str] | None = None) -> str:
    cmd = ["git", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise ArrangementGitError(f"git failed ({proc.returncode}): {' '.join(cmd)}\n{stderr}\n{stdout}".strip())
    return (proc.stdout or "").strip()


def _git_root_dir() -> Path:
    root = getattr(settings, "ARRANGEMENT_GIT_ROOT", None)
    if root:
        return Path(root)
    # backend/backend is BASE_DIR; keep repos near it by default
    return Path(settings.BASE_DIR) / "arrangement_git_repos"


def init_repo(arrangement: Arrangement) -> str:
    """
    Ensure a per-arrangement bare git repo exists on disk and is referenced
    by a GitRepo row (ensembles.GitRepo).
    """
    if arrangement.pk is None:
        raise ArrangementGitError("Arrangement must be saved before initializing a repo.")

    root = _git_root_dir()
    root.mkdir(parents=True, exist_ok=True)

    # Source of truth is the GitRepo model (not Arrangement fields).
    repo_row = GitRepo.objects.filter(arrangement=arrangement).order_by("id").first()
    if repo_row is None:
        repo_path = str(root / f"arr_{arrangement.id}.git")
        repo_row = GitRepo.objects.create(arrangement=arrangement, repo_path=repo_path)
    else:
        repo_path = repo_row.repo_path

    repo_dir = Path(repo_path)
    if not repo_dir.exists():
        repo_dir.mkdir(parents=True, exist_ok=True)

    # If it doesn't look like a git repo yet, initialize it as bare.
    if not (repo_dir / "HEAD").exists():
        # Prefer initializing with main to avoid master-branch warnings.
        try:
            _run_git(["init", "--bare", "--initial-branch=main", str(repo_dir)])
        except ArrangementGitError:
            # Fallback for older git versions that don't support --initial-branch.
            _run_git(["init", "--bare", str(repo_dir)])

    # Configure scoreforge merge driver (repo-local)
    # This enables `.gitattributes` with `merge=scoreforge` to work without global config.
    driver_cmd = "python -m ensembles.services.scoreforge_merge_driver %O %A %B"
    _run_git(["--git-dir", str(repo_dir), "config", "merge.scoreforge.name", "ScoreForge canonical merge"])
    _run_git(["--git-dir", str(repo_dir), "config", "merge.scoreforge.driver", driver_cmd])

    # Ensure default branch exists as the symbolic HEAD (doesn't create a commit).
    default_branch = "main"
    _run_git(["--git-dir", str(repo_dir), "symbolic-ref", "HEAD", f"refs/heads/{default_branch}"])

    return repo_path


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
    Create a commit in the arrangement's bare repo containing the payload_dir contents.
    Returns the created Commit row.
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

        _run_git(["clone", str(repo_path), str(workdir)])

        # If this is a brand-new repo without commits, clone will have no branch checked out.
        # Ensure we're on default_branch.
        try:
            _run_git(["checkout", default_branch], cwd=workdir)
        except ArrangementGitError:
            _run_git(["checkout", "-b", default_branch], cwd=workdir)

        # Copy payload into repo workdir
        for src in payload_dir.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(payload_dir)
            dest = workdir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())

        _run_git(["add", "-A"], cwd=workdir)
        status_porcelain = _run_git(["status", "--porcelain"], cwd=workdir)

        # If canonical payload is unchanged, reuse current HEAD commit.
        if not status_porcelain.strip():
            sha = _run_git(["rev-parse", "HEAD"], cwd=workdir)
            existing = Commit.objects.filter(git_repo=git_repo, sha=sha).first()
            if existing is not None:
                return existing
            raise ArrangementGitError(
                "No changes detected in canonical snapshot and no existing Commit row found for HEAD."
            )

        env: dict[str, str] = {}
        if timestamp is not None:
            # Git expects an ISO-ish format or unix timestamp; ISO works.
            iso = timestamp.isoformat()
            env["GIT_AUTHOR_DATE"] = iso
            env["GIT_COMMITTER_DATE"] = iso

        _run_git(
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

        sha = _run_git(["rev-parse", "HEAD"], cwd=workdir)
        parent_sha = _run_git(["rev-parse", "HEAD^"], cwd=workdir) if _has_parent(workdir) else None

        _run_git(["push", "origin", default_branch], cwd=workdir)

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
        _run_git(["rev-parse", "HEAD^"], cwd=workdir)
        return True
    except ArrangementGitError:
        return False


def tag_version(arrangement: Arrangement, sha: str, tag: str) -> None:
    repo_path = Path(init_repo(arrangement))
    _run_git(["--git-dir", str(repo_path), "tag", "-f", tag, sha])

