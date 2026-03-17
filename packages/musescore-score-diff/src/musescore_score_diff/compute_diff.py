import xml.etree.ElementTree as ET

from .utils import get_staves, extract_measures
from .utils import State


def lcs(seq1: list[str], seq2: list[str]) -> list[list[int]]:
    """Compute LCS DP table."""
    n, m = len(seq1), len(seq2)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq1[i] == seq2[j]:
                L[i+1][j+1] = L[i][j] + 1
            else:
                L[i+1][j+1] = max(L[i][j+1], L[i+1][j])
    return L

def backtrack(L: list[list[int]], measures1, measures2)-> dict[int, State]:
    """Backtrack through LCS to reconstruct diff."""
    diffs = {}
    i, j = len(measures1), len(measures2)

    while i > 0 or j > 0:
        # Case 1: identical hash (unchanged)
        if i > 0 and j > 0 and measures1[i-1][1] == measures2[j-1][1]:
            diffs[measures1[i-1][0]] = State.UNCHANGED
            i -= 1
            j -= 1

        # Case 2: both measures exist, same number but different hash (modified)
        elif i > 0 and j > 0 and measures1[i-1][0] == measures2[j-1][0]:
            diffs[measures1[i-1][0]] = State.MODIFIED
            i -= 1
            j -= 1

        # Case 3: added
        elif j > 0 and (i == 0 or L[i][j-1] >= L[i-1][j]):
            diffs[measures2[j-1][0]] = State.INSERTED
            j -= 1

        # Case 4: removed
        elif i > 0 and (j == 0 or L[i][j-1] < L[i-1][j]):
            diffs[measures1[i-1][0]] = State.REMOVED
            i -= 1

    return diffs

def compute_diff(file1: str, file2: str) -> dict[int, dict[int, State]]:

    staves1, staves2 = get_staves(file1), get_staves(file2)
    assert len(staves1) == len(staves2), "Currently, only supported on files that have the same # of instruments"
    i = 1
    res = {}
    for staff1, staff2 in zip(staves1, staves2):
        measures1, measures2 = extract_measures(staff1), extract_measures(staff2)

        seq1 = [h for (_, h, _) in measures1]
        seq2 = [h for (_, h, _) in measures2]

        L = lcs(seq1, seq2)
        res[i] = backtrack(L, measures1, measures2)
        i += 1
    return res
