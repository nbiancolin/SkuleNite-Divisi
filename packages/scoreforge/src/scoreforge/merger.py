"""Score merging functionality for canonical dataclass score models."""

from __future__ import annotations

from typing import Dict, Tuple

from scoreforge.models import Measure, Part, Score, Staff
from scoreforge.parser import canonical_hash


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
    return canonical_hash(measure)


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
    def score_maps(score: Score) -> dict[tuple[str, int, int], Measure]:
        out: dict[tuple[str, int, int], Measure] = {}
        for part in score.parts:
            for staff in part.staves:
                for measure in staff.measures:
                    out[(part.part_id, staff.staff_id, measure.number)] = measure
        return out

    base_measures = score_maps(base_score)
    head_measures = score_maps(head_score)
    user_measures = score_maps(user_score)
    all_keys = set(base_measures) | set(head_measures) | set(user_measures)

    conflicts: Dict[Tuple[str, int], Tuple[Measure, Measure]] = {}
    merged_measures: dict[tuple[str, int, int], Measure] = {}
    for part_id, staff_id, number in sorted(all_keys):
        b = base_measures.get((part_id, staff_id, number))
        h = head_measures.get((part_id, staff_id, number))
        u = user_measures.get((part_id, staff_id, number))

        if h == u:
            chosen = h
        elif b == h:
            chosen = u
        elif b == u:
            chosen = h
        else:
            if h is not None and u is not None:
                conflicts[(part_id, number)] = (h, u)
            continue

        if chosen is not None:
            merged_measures[(part_id, staff_id, number)] = chosen

    if conflicts:
        raise MergeConflict(conflicts)

    part_template: dict[str, Part] = {}
    for source in (head_score, user_score, base_score):
        for part in source.parts:
            part_template.setdefault(part.part_id, part)

    merged_parts: list[Part] = []
    part_ids = sorted({k[0] for k in merged_measures.keys()})
    for part_id in part_ids:
        template = part_template.get(part_id)
        if template is None:
            continue
        staves: list[Staff] = []
        staff_ids = sorted({k[1] for k in merged_measures.keys() if k[0] == part_id})
        for staff_id in staff_ids:
            base_staff = next((s for s in template.staves if s.staff_id == staff_id), None)
            if base_staff is None:
                continue
            measure_nums = sorted(
                n for (pid, sid, n) in merged_measures if pid == part_id and sid == staff_id
            )
            measures = tuple(merged_measures[(part_id, staff_id, n)] for n in measure_nums)
            staves.append(
                Staff(
                    staff_id=staff_id,
                    measures=measures,
                    clef=base_staff.clef,
                    is_drum=base_staff.is_drum,
                )
            )
        merged_parts.append(
            Part(
                part_id=template.part_id,
                instrument_id=template.instrument_id,
                name=template.name,
                staves=tuple(staves),
            )
        )

    metadata = head_score.metadata if base_score.metadata == user_score.metadata else user_score.metadata
    division = head_score.division if base_score.division == user_score.division else user_score.division
    return Score(metadata=metadata, parts=tuple(merged_parts), division=division)
