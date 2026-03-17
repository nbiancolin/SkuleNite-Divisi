import pytest
import os
import shutil

# =======================
# Test Constants
# =======================

OUTPUT_DIRECTORY = "tests/processing"


@pytest.fixture(scope="module", autouse=True)
def cleanup_processed_scores():
    #Before all tests run
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    yield

    #After all tests run
    # clean up temp-processed directory
    shutil.rmtree(OUTPUT_DIRECTORY)