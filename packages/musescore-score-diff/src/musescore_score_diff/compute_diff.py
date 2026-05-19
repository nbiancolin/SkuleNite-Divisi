import xml.etree.ElementTree as ET

from .utils import extract_measures, pair_staves_by_part_order, pair_staves_by_track_name
from .utils import State


def _pair_staves(score1: ET.Element, score2: ET.Element) -> list[tuple[ET.Element, ET.Element]]:
    try:
        return pair_staves_by_part_order(score1, score2)
    except ValueError:
        try:
            return pair_staves_by_track_name(score1, score2)
        except ValueError:
            staves1 = score1.findall("Staff")
            staves2 = score2.findall("Staff")
            if len(staves1) != len(staves2):
                raise
            return list(zip(staves1, staves2))


def lcs(seq1: list[str], seq2: list[str]) -> list[list[int]]:
    """Compute LCS DP table."""
    n, m = len(seq1), len(seq2)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq1[i] == seq2[j]:
                L[i + 1][j + 1] = L[i][j] + 1
            else:
                L[i + 1][j + 1] = max(L[i][j + 1], L[i + 1][j])
    return L


def backtrack(L: list[list[int]], measures1, measures2) -> list[State]:
    """Backtrack through LCS to reconstruct an ordered edit script (left-to-right)."""
    ops: list[State] = []
    i, j = len(measures1), len(measures2)

    while i > 0 or j > 0:
        if i > 0 and j > 0 and measures1[i - 1][1] == measures2[j - 1][1]:
            ops.append(State.UNCHANGED)
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and measures1[i - 1][0] == measures2[j - 1][0]:
            ops.append(State.MODIFIED)
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or L[i][j - 1] >= L[i - 1][j]):
            ops.append(State.INSERTED)
            j -= 1
        elif i > 0 and (j == 0 or L[i][j - 1] < L[i - 1][j]):
            ops.append(State.REMOVED)
            i -= 1

    ops.reverse()
    return ops


def _load_score(path: str) -> ET.Element:
    tree = ET.parse(path)
    score = tree.getroot().find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")
    return score


def compute_diff(file1: str, file2: str) -> dict[int, list[State]]:
    """
    Compare two MuseScore files staff-by-staff.

    Returns ``{staff_index: [State, ...]}`` where ``staff_index`` is 1-based in
    score1 part/staff order (same order as ``mark_diffs_unified`` / merge expect).
    """
    score1 = _load_score(file1)
    score2 = _load_score(file2)
    pairs = _pair_staves(score1, score2)

    res: dict[int, list[State]] = {}
    for staff_idx, (staff1, staff2) in enumerate(pairs, start=1):
        measures1, measures2 = extract_measures(staff1), extract_measures(staff2)
        seq1 = [h for (_, h, _) in measures1]
        seq2 = [h for (_, h, _) in measures2]
        L = lcs(seq1, seq2)
        res[staff_idx] = backtrack(L, measures1, measures2)
    return res
