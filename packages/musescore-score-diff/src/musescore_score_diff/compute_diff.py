from collections import defaultdict

import xml.etree.ElementTree as ET

from .alignment import RowKind, StaffAlignment, align_staves
from .utils import State, extract_measures


def _pair_staves(score1: ET.Element, score2: ET.Element) -> list[tuple[ET.Element, ET.Element]]:
    """Pair staves that exist on both sides (matched rows only)."""
    return align_staves(score1, score2).matched_pairs()


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


def _measure_diff_ops(staff1: ET.Element, staff2: ET.Element) -> list[State]:
    measures1, measures2 = extract_measures(staff1), extract_measures(staff2)
    seq1 = [h for (_, h, _) in measures1]
    seq2 = [h for (_, h, _) in measures2]
    L = lcs(seq1, seq2)
    return backtrack(L, measures1, measures2)


def _ops_for_row(row) -> list[State]:
    if row.kind in (RowKind.MATCHED, RowKind.RENAMED):
        assert row.staff_left is not None and row.staff_right is not None
        return _measure_diff_ops(row.staff_left, row.staff_right)
    if row.kind == RowKind.LEFT_ONLY:
        assert row.staff_left is not None
        n = len(row.staff_left.findall("Measure"))
        return [State.REMOVED] * n
    if row.kind == RowKind.RIGHT_ONLY:
        assert row.staff_right is not None
        n = len(row.staff_right.findall("Measure"))
        return [State.INSERTED] * n
    raise ValueError(f"Unknown alignment row kind: {row.kind}")


def _synchronize_ops_across_part_staves(
    alignment: StaffAlignment, diffs: dict[int, list[State]]
) -> None:
    """
    Align INSERTED/REMOVED steps across staves in the same part.

    Per-staff LCS can place insert/delete at different indices; bar lines must line
    up in the score. MODIFIED vs UNCHANGED stays per staff (bass may be unchanged
    while treble differs).
    """
    groups: dict[int, list[tuple[int, AlignmentRow]]] = defaultdict(list)
    for pair_id, row in enumerate(alignment.rows, start=1):
        if row.kind not in (RowKind.MATCHED, RowKind.RENAMED):
            continue
        if row.part_index_left is None:
            continue
        groups[row.part_index_left].append((pair_id, row))

    for members in groups.values():
        if len(members) < 2:
            continue
        ref_pid, ref_row = members[0]
        assert ref_row.staff_left is not None and ref_row.staff_right is not None
        structural = _measure_diff_ops(ref_row.staff_left, ref_row.staff_right)

        for pair_id, row in members:
            own = diffs[pair_id]
            synced: list[State] = []
            for step, struct in enumerate(structural):
                if struct in (State.INSERTED, State.REMOVED):
                    synced.append(struct)
                elif step < len(own) and own[step] in (State.INSERTED, State.REMOVED):
                    # Per-staff LCS mis-placed insert/delete; keep bar alignment only.
                    synced.append(State.UNCHANGED)
                elif step < len(own):
                    synced.append(own[step])
                else:
                    synced.append(State.UNCHANGED)
            diffs[pair_id] = synced


def _load_score(path: str) -> ET.Element:
    tree = ET.parse(path)
    score = tree.getroot().find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")
    return score


def compute_diff_with_alignment(
    file1: str, file2: str
) -> tuple[dict[int, list[State]], StaffAlignment]:
    """
    Compare two MuseScore files staff-by-staff.

    Returns ``(diffs, alignment)`` where ``diffs`` maps 1-based pair index (union
    display order) to measure edit states.
    """
    score1 = _load_score(file1)
    score2 = _load_score(file2)
    alignment = align_staves(score1, score2)

    res: dict[int, list[State]] = {}
    for pair_id, row in enumerate(alignment.rows, start=1):
        res[pair_id] = _ops_for_row(row)
    _synchronize_ops_across_part_staves(alignment, res)
    return res, alignment


def compute_diff(file1: str, file2: str) -> dict[int, list[State]]:
    """
    Compare two MuseScore files staff-by-staff.

    Returns ``{pair_index: [State, ...]}`` where pair index follows alignment row
    order (same order as unified diff display / merge).
    """
    diffs, _ = compute_diff_with_alignment(file1, file2)
    return diffs
