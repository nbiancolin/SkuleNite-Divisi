# Plugin Tests

import pytest
import subprocess
from logging import getLogger

logger = getLogger("app")


# =========================================
# System Layout Export Plugin Tests
# =========================================



# TODO: doesnt work on windows bc it forks the process i guess?
# MUSESCORE_BIN_PATH = "C:\\Program Files\\MuseScore 4\\bin\\MuseScore4.exe"
MUSESCORE_BIN_PATH = "musescore"

def _run_musescore(*args, **kwargs):
    args = [MUSESCORE_BIN_PATH, *args]
    return subprocess.run(
                    args, 
                    check=True,
                    timeout=60,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )


def test_output_format_correct():
    TEST_FILE = "..\\..\\packages\\musescore-score-diff\\tests\\fixtures\\Test-Score.mscz"

    args = [TEST_FILE, "--plugin", "system-layout-export"]

    try:
        proc = _run_musescore(*args)

        stdout_bytes = proc.stdout
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        logger.info(f"MuseScore stdout length: {len(stdout_bytes)} bytes")
        logger.info(f"MuseScore stderr length: {len(proc.stderr)} bytes")

        if proc.stderr:
            logger.info(f"MuseScore stderr (first 500 chars): {proc.stderr.decode('utf-8', errors='replace')[:500]}")

    except subprocess.TimeoutExpired:
        logger.error("MuseScore timed out")
        raise 
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode(errors="ignore") if e.stderr else "Unknown error"
        logger.error(f"MuseScore error: {stderr_msg}")
        raise
    
    assert False, stdout_text