from musescore_score_diff.utils import get_staves, extract_measures


def assert_scores_match(file1: str, file2: str) -> bool:
    lhs_staves, rhs_staves = get_staves(file1), get_staves(file2)

    assert len(lhs_staves) == len(rhs_staves), (
        f"Scores have different amt of staves\n :LHS: {len(lhs_staves)} RHS: {len(rhs_staves)}"
    )

    for staff1, staff2 in zip(lhs_staves, rhs_staves):
        measures1, measures2 = extract_measures(staff1), extract_measures(staff2)

        assert len(measures1) == len(measures2), (
            f"Staves have different number of measures\n measures1: {measures1}, measures2: {measures2}"
        )

        for i in range(len(measures1)):
            hash1, hash2 = measures1[i][1], measures2[i][1]

            assert hash1 == hash2, f"Measure {i} have different hashes\n LHS: {measures1[i]}, RHS: {measures2[i]}"
    
    return True