import pytest

from musescore_part_formatter.estimating_formatting_params import (
    predict_style_params,
    normalize_staff_spacing_strategy,
)


@pytest.mark.parametrize(
    "input_param, input_param_value, res_param, res_param_value",
    [
        ("num_staves", 6, "staff_spacing", "1.65"),
        ("num_staves", 12, "staff_spacing", "1.575"),
    ],
)
def test_predict_style_params(input_param, input_param_value, res_param, res_param_value):
    score_info = {input_param: input_param_value}

    res = predict_style_params(score_info)
    assert res[res_param] == res_param_value


def test_predict_style_params_empty_without_stave_count():
    assert predict_style_params({}) == {}


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("predict", "predict"),
        ("preserve", "preserve"),
        ("override", "override"),
        (None, "predict"),
        ("unknown", "predict"),
    ],
)
def test_normalize_staff_spacing_strategy(raw, expected):
    assert normalize_staff_spacing_strategy(raw) == expected
