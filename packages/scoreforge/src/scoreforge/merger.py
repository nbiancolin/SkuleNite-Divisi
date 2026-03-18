"""Score merging functionality for combining scores based on their canonical form."""

import hashlib
from typing import Dict, List, Tuple

from scoreforge.models import Score, Measure


class MergeConflict(Exception):
    """Exception raised when merging two scores results in conflicts.

    This exception contains information about all conflicting measures,
    allowing the caller to inspect and resolve conflicts programmatically.

    Attributes:
        conflicts: Dictionary mapping (part_id, measure_number) tuples to
            tuples of (measure_from_head, measure_from_user). Each conflict
            represents a measure that exists in both head and user with different content.
        message: Human-readable error message describing the conflicts
    """

    def __init__(
        self,
        conflicts: Dict[Tuple[str, int], Tuple[Measure, Measure]],
        message: str | None = None
    ):
        """Initialize a MergeConflict exception.

        Args:
            conflicts: Dictionary of conflicts, keyed by (part_id, measure_number)
            message: Optional custom error message
        """
        self.conflicts = conflicts
        if message is None:
            conflict_count = len(conflicts)
            conflict_details = ", ".join(
                f"part '{part_id}' measure {measure_num}"
                for part_id, measure_num in conflicts.keys()
            )
            message = (
                f"Merge conflict: {conflict_count} measure(s) have conflicting content. "
                f"Conflicts in: {conflict_details}. "
                f"Access conflict details via the 'conflicts' attribute."
            )
        super().__init__(message)


def _hash_measure(measure: Measure) -> str:
    """Return a stable hash of the measure's content for quick comparison."""
    raw = str(measure)
    normalized = "".join(raw.split()).encode("utf-8")
    return hashlib.md5(normalized).hexdigest()


def _lcs_align(seq_base: List[str], seq_other: List[str]) -> List[Tuple[int | None, int | None]]:
    """
    Align seq_base with seq_other using LCS.
    Returns list of (base_idx, other_idx) for each match; base_idx or other_idx is None
    for insertions. Walk through in order of the merged sequence.
    """
    n, m = len(seq_base), len(seq_other)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if seq_base[i] == seq_other[j]:
                L[i + 1][j + 1] = L[i][j] + 1
            else:
                L[i + 1][j + 1] = max(L[i][j + 1], L[i + 1][j])

    # Backtrack to get aligned pairs
    result: List[Tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and seq_base[i - 1] == seq_other[j - 1]:
            result.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or L[i][j - 1] >= L[i - 1][j]):
            result.append((None, j - 1))
            j -= 1
        elif i > 0 and (j == 0 or L[i][j - 1] < L[i - 1][j]):
            result.append((i - 1, None))
            i -= 1

    result.reverse()
    return result


def three_way_merge_scores(user_score: Score, base_score: Score, head_score: Score) -> Score:
    """
    Perform a 3-way merge between scores.

    Merge user_score (local changes) and head_score (remote changes) using
    base_score as the common ancestor. Uses LCS-based alignment to handle
    measure insertions and deletions correctly. When both head and user
    modified the same measure differently, raises MergeConflict.

    In a git-like workflow:
    - base_score = last synced/pulled version
    - head_score = current remote (e.g. origin/main)
    - user_score = local working changes

    Args:
        user_score: The score the user is trying to merge (local)
        base_score: The base version both user and head diverged from
        head_score: The current head score in the repo (remote)

    Returns:
        Merged Score combining user and head changes

    Raises:
        MergeConflict: When both head and user modified the same measure
    """
    from scoreforge.models import Part, Measure

    def _part_by_id(score: Score, part_id: str) -> Part | None:
        for p in score.parts:
            if p.part_id == part_id:
                return p
        return None

    part_ids = (
        {p.part_id for p in base_score.parts}
        | {p.part_id for p in head_score.parts}
        | {p.part_id for p in user_score.parts}
    )

    conflicts: Dict[Tuple[str, int], Tuple[Measure, Measure]] = {}
    merged_parts: list[Part] = []

    for part_id in sorted(part_ids):
        base_part = _part_by_id(base_score, part_id)
        head_part = _part_by_id(head_score, part_id)
        user_part = _part_by_id(user_score, part_id)

        if base_part is None and head_part is None:
            if user_part is not None:
                merged_parts.append(user_part)
            continue
        if base_part is None and user_part is None:
            if head_part is not None:
                merged_parts.append(head_part)
            continue
        if head_part is None and user_part is None:
            if base_part is not None:
                merged_parts.append(base_part)
            continue

        base_part = base_part or Part(part_id=part_id, measures=[])
        head_part = head_part or Part(part_id=part_id, measures=[])
        user_part = user_part or Part(part_id=part_id, measures=[])

        base_measures = list(base_part.measures)
        head_measures = list(head_part.measures)
        user_measures = list(user_part.measures)

        base_hashes = [_hash_measure(m) for m in base_measures]
        head_hashes = [_hash_measure(m) for m in head_measures]
        user_hashes = [_hash_measure(m) for m in user_measures]

        align_base_head = _lcs_align(base_hashes, head_hashes)
        align_base_user = _lcs_align(base_hashes, user_hashes)

        base_to_head: Dict[int, int | None] = {}
        base_to_user: Dict[int, int | None] = {}
        head_insertions: List[int] = []
        user_insertions: List[int] = []

        for bi, hi in align_base_head:
            if bi is not None:
                base_to_head[bi] = hi
            elif hi is not None:
                head_insertions.append(hi)

        for bi, ui in align_base_user:
            if bi is not None:
                base_to_user[bi] = ui
            elif ui is not None:
                user_insertions.append(ui)

        # When both sides have the same length as base, use position-based alignment
        # to correctly detect conflicts (LCS treats different content as remove+insert
        # and would add both versions).
        same_length = (len(base_measures) == len(head_measures) == len(user_measures))
        if same_length:
            base_to_head = {i: i for i in range(len(base_measures))}
            base_to_user = {i: i for i in range(len(user_measures))}
            head_insertions = []
            user_insertions = []

        merged_measures: list[Measure] = []
        out_measure_num = 1
        head_insertions_idx = 0
        user_insertions_idx = 0
        user_insertions_sorted = sorted(user_insertions)
        head_insertions_sorted = sorted(head_insertions)

        for base_idx in range(len(base_measures)):
            head_idx = base_to_head.get(base_idx)
            user_idx = base_to_user.get(base_idx)

            while user_insertions_idx < len(user_insertions_sorted):
                ui = user_insertions_sorted[user_insertions_idx]
                if user_idx is not None and ui >= user_idx:
                    break
                merged_measures.append(
                    Measure(number=out_measure_num, events=user_measures[ui].events,
                            key_sig=user_measures[ui].key_sig, time_sig=user_measures[ui].time_sig,
                            irregular=user_measures[ui].irregular,
                            measure_len=user_measures[ui].measure_len)
                )
                out_measure_num += 1
                user_insertions_idx += 1

            while head_insertions_idx < len(head_insertions_sorted):
                hi = head_insertions_sorted[head_insertions_idx]
                if head_idx is not None and hi >= head_idx:
                    break
                merged_measures.append(
                    Measure(number=out_measure_num, events=head_measures[hi].events,
                            key_sig=head_measures[hi].key_sig, time_sig=head_measures[hi].time_sig,
                            irregular=head_measures[hi].irregular)
                )
                out_measure_num += 1
                head_insertions_idx += 1

            base_meas = base_measures[base_idx]
            head_meas = head_measures[head_idx] if head_idx is not None else None
            user_meas = user_measures[user_idx] if user_idx is not None else None

            base_hash = base_hashes[base_idx]
            head_hash = _hash_measure(head_meas) if head_meas else None
            user_hash = _hash_measure(user_meas) if user_meas else None

            if head_meas and user_meas:
                if base_hash == head_hash == user_hash:
                    merged_measures.append(
                        Measure(number=out_measure_num, events=base_meas.events,
                                key_sig=base_meas.key_sig, time_sig=base_meas.time_sig,
                                irregular=base_meas.irregular,
                                measure_len=base_meas.measure_len)
                    )
                elif base_hash == head_hash:
                    merged_measures.append(
                        Measure(number=out_measure_num, events=user_meas.events,
                                key_sig=user_meas.key_sig, time_sig=user_meas.time_sig,
                                irregular=user_meas.irregular,
                                measure_len=user_meas.measure_len)
                    )
                elif base_hash == user_hash:
                    merged_measures.append(
                        Measure(number=out_measure_num, events=head_meas.events,
                                key_sig=head_meas.key_sig, time_sig=head_meas.time_sig,
                                irregular=head_meas.irregular,
                                measure_len=head_meas.measure_len)
                    )
                elif head_hash == user_hash:
                    merged_measures.append(
                        Measure(number=out_measure_num, events=head_meas.events,
                                key_sig=head_meas.key_sig, time_sig=head_meas.time_sig,
                                irregular=head_meas.irregular,
                                measure_len=head_meas.measure_len)
                    )
                else:
                    conflicts[(part_id, out_measure_num)] = (head_meas, user_meas)
                out_measure_num += 1
            elif head_meas and not user_meas:
                if base_hash == head_hash:
                    pass  # User removed
                else:
                    empty_meas = Measure(number=out_measure_num, events=[])
                    conflicts[(part_id, out_measure_num)] = (head_meas, empty_meas)
                    out_measure_num += 1
            elif user_meas and not head_meas:
                if base_hash == user_hash:
                    pass  # Head removed
                else:
                    empty_meas = Measure(number=out_measure_num, events=[])
                    conflicts[(part_id, out_measure_num)] = (empty_meas, user_meas)
                    out_measure_num += 1

        for hi in head_insertions_sorted[head_insertions_idx:]:
            merged_measures.append(
                Measure(number=out_measure_num, events=head_measures[hi].events,
                        key_sig=head_measures[hi].key_sig, time_sig=head_measures[hi].time_sig,
                        irregular=head_measures[hi].irregular,
                        measure_len=head_measures[hi].measure_len)
            )
            out_measure_num += 1

        for ui in user_insertions_sorted[user_insertions_idx:]:
            merged_measures.append(
                Measure(number=out_measure_num, events=user_measures[ui].events,
                        key_sig=user_measures[ui].key_sig, time_sig=user_measures[ui].time_sig,
                        irregular=user_measures[ui].irregular)
            )
            out_measure_num += 1

        if not conflicts:
            merged_parts.append(Part(part_id=part_id, measures=merged_measures))

    if conflicts:
        raise MergeConflict(conflicts)

    score_id = user_score.score_id or head_score.score_id or base_score.score_id
    return Score(parts=merged_parts, score_id=score_id)
