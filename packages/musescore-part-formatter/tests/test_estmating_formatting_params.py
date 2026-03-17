import pytest

from musescore_part_formatter.estimating_formatting_params import predict_style_params


@pytest.mark.parametrize(
    "input_param, input_param_value, res_param, res_param_value", [
        ("num_staves", 6, "staff_spacing", '1.65'),
        ("num_staves", 12, "staff_spacing", '1.575'),
        #TODO: Add more of these once more params are confuigured to be auto detected
        #TODO: Manually check these values on scores with the right # of instruments
    ]
)
def test_predict_style_params(input_param, input_param_value, res_param, res_param_value):
    score_info = {input_param: input_param_value}
    
    res = predict_style_params(score_info)
    assert res[res_param] == res_param_value


#TODO: Write tests that test that the getter fields get the right values from sample mscz files