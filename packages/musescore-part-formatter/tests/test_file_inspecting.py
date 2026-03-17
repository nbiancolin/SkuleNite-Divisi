import pytest
import shutil
import tempfile

from musescore_part_formatter.main import get_score_attributes, set_score_attributes

MUSESCORE_PATH = "tests/test-data/New-Test-Score.mscz"


@pytest.fixture(scope="function")
def musescore_path():
    """Creates a copy of the file to use for testing,
    and cleans it up after"""

    with tempfile.TemporaryDirectory() as workdir:
        res = shutil.copy(MUSESCORE_PATH, workdir)
        yield res
        # Should cleanup afterwards I think !


def test_title_properties_retrieved_correctly():
    input_path = MUSESCORE_PATH

    res = get_score_attributes(input_path)

    EXPECTED_VALUES = {
        "title": "Test Score",
        "subtitle": "Subtitle",
        "composer": "arr. Nicholas Biancolin",
    }

    for prop, value in EXPECTED_VALUES.items():
        assert res[prop] == value


def test_meta_properties_retrieved_correctly():
    input_path = MUSESCORE_PATH

    res = get_score_attributes(input_path)

    EXPECTED_VALUES = {
        "workTitle": "Test Score",
        "subtitle": "Subtitle",
        "composer": "arr. Nicholas Biancolin",
        "arranger": None,
    }

    for prop, value in EXPECTED_VALUES.items():
        assert res[f"meta_{prop}"] == value


def test_num_instruments_retrieved_correctly():
    input_path = MUSESCORE_PATH

    res = get_score_attributes(input_path)

    EXPECTED_VALUES = {
        "num_instruments": 5,
        "num_staves": 6,
    }

    for prop, value in EXPECTED_VALUES.items():
        assert res[prop] == value


def test_time_signatures_retrieved_correctly():
    input_path = MUSESCORE_PATH

    res = get_score_attributes(input_path)

    EXPECTED_VALUES = {"time_signatures": ["4/4"]}

    for prop, value in EXPECTED_VALUES.items():
        assert res[prop] == value


def test_set_score_properties(musescore_path):
    properties_to_set = {
        "title": "New Title",
        "subtitle": "New Subtitle",
        "composer": "New Composer",
    }

    set_score_attributes(musescore_path, properties_to_set)

    res = get_score_attributes(musescore_path)

    for k in properties_to_set.keys():
        assert res[k] == properties_to_set[k]


def test_set_score_meta_properties(musescore_path):
    properties_to_set = {
        "meta_workTitle": "New Title",
        "meta_composer": "New Composer",
        "meta_arranger": "New Arranger",
    }

    set_score_attributes(musescore_path, properties_to_set)

    res = get_score_attributes(musescore_path)

    print(res)

    for k in properties_to_set.keys():
        assert res[k] == properties_to_set[k], res
