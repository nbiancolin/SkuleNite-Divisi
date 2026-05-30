# Plugin Tests

import pytest

from plugin_runner import run_system_layout_export


def test_system_layout_export_output_format():
    result = run_system_layout_export("./fixtures/Test-Score.mscz")

    assert isinstance(result, dict)
    assert result.get("staff_id") == "1"
    assert isinstance(result.get("systems"), list)
    assert len(result["systems"]) > 0

    measure_numbers = []
    for system in result["systems"]:
        assert isinstance(system, list)
        assert len(system) > 0
        for measure_no in system:
            assert isinstance(measure_no, int)
            assert measure_no >= 0
            measure_numbers.append(measure_no)

    # Measures should appear in order with no duplicates.
    assert measure_numbers == sorted(set(measure_numbers))
    assert measure_numbers == list(range(len(measure_numbers)))


def test_system_layout_export_missing_score():
    with pytest.raises(FileNotFoundError):
        run_system_layout_export("./fixtures/does-not-exist.mscz")
