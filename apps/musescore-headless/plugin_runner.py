"""Run MuseScore legacy plugins via the extensions CLI."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

MUSESCORE_BIN = os.environ.get("MUSESCORE_BIN", "musescore")
SYSTEM_LAYOUT_EXPORT_URI = (
    "musescore://extensions/v1/system-layout-export.qml?action=main"
)
SYSTEM_LAYOUT_EXPORT_OUTPUT = Path("/tmp/system-layout-export.json")


class MuseScorePluginError(RuntimeError):
    pass


def run_system_layout_export(score_path: str | Path, *, timeout: int = 120) -> dict:
    """Run the system-layout-export plugin and return parsed JSON."""
    score_path = Path(score_path).resolve()
    if not score_path.is_file():
        raise FileNotFoundError(score_path)

    SYSTEM_LAYOUT_EXPORT_OUTPUT.unlink(missing_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as job_file:
        json.dump(
            [
                {
                    "in": str(score_path),
                    "out": "/tmp/system-layout-export-dummy.pdf",
                }
            ],
            job_file,
        )
        job_path = job_file.name

    try:
        proc = subprocess.run(
            [
                MUSESCORE_BIN,
                "-j",
                job_path,
                "--extension",
                SYSTEM_LAYOUT_EXPORT_URI,
            ],
            check=False,
            timeout=timeout,
            capture_output=True,
        )
    finally:
        Path(job_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise MuseScorePluginError(
            f"MuseScore exited with code {proc.returncode}: {stderr[-2000:]}"
        )

    if not SYSTEM_LAYOUT_EXPORT_OUTPUT.is_file():
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise MuseScorePluginError(
            "Plugin did not write output file "
            f"{SYSTEM_LAYOUT_EXPORT_OUTPUT}. stderr: {stderr[-2000:]}"
        )

    return json.loads(SYSTEM_LAYOUT_EXPORT_OUTPUT.read_text(encoding="utf-8"))
