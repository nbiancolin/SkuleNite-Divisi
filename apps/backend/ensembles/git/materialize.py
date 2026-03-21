"""
Build MuseScore files from a committed canonical tree (checkout + scoreforge).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage

from scoreforge.cli import json_to_mscz

from ensembles.git.repo import init_repo
from ensembles.git.runner import run_git
from ensembles.models import Arrangement, ArrangementVersion


def _build_mscz_in_workdir(*, workdir: Path, mscz_out_path: Path) -> None:
    canonical_json_path = workdir / "canonical.json"
    template_mscz_path = workdir / "canonical.mscz"

    if template_mscz_path.is_file():
        json_to_mscz(str(canonical_json_path), str(mscz_out_path), str(template_mscz_path))
    else:
        json_to_mscz(str(canonical_json_path), str(mscz_out_path))


def build_mscz_bytes_from_commit(*, arrangement: Arrangement, commit_sha: str) -> bytes:
    """
    Check out ``commit_sha`` from the arrangement bare repo and return the built ``.mscz`` bytes.
    Does not write to Django storage.
    """
    repo_path = init_repo(arrangement)

    with tempfile.TemporaryDirectory(prefix="arr_from_commit_dl_") as tmp:
        tmp_dir = Path(tmp)
        workdir = tmp_dir / "work"
        mscz_out_path = tmp_dir / "commit.mscz"

        run_git(["clone", "--quiet", repo_path, str(workdir)])
        run_git(["checkout", "--quiet", commit_sha], cwd=workdir)

        _build_mscz_in_workdir(workdir=workdir, mscz_out_path=mscz_out_path)
        return mscz_out_path.read_bytes()


def materialize_commit_mscz_to_version(*, arrangement: Arrangement, commit_sha: str, version: ArrangementVersion) -> None:
    """
    Check out ``commit_sha`` from the arrangement bare repo, convert ``canonical.json`` to ``.mscz``,
    and store the result at ``version.mscz_file_key``.
    """
    repo_path = init_repo(arrangement)

    with tempfile.TemporaryDirectory(prefix="arr_from_commit_") as tmp:
        tmp_dir = Path(tmp)
        workdir = tmp_dir / "work"
        mscz_out_path = tmp_dir / "commit.mscz"

        run_git(["clone", "--quiet", repo_path, str(workdir)])
        run_git(["checkout", "--quiet", commit_sha], cwd=workdir)

        _build_mscz_in_workdir(workdir=workdir, mscz_out_path=mscz_out_path)

        with open(mscz_out_path, "rb") as f:
            default_storage.save(version.mscz_file_key, File(f))
