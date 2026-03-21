from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ensembles.git.exceptions import ArrangementGitError


def run_git(
    args: list[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Run ``git`` with ``args`` and return stdout (stripped). Raises :class:`ArrangementGitError` on failure."""
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
        raise ArrangementGitError(
            f"git failed ({proc.returncode}): {' '.join(cmd)}\n{stderr}\n{stdout}".strip()
        )
    return (proc.stdout or "").strip()
