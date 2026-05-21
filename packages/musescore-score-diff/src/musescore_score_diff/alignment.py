"""Staff/part alignment between two MuseScore scores."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

from .utils import (
    _hash_measure,
    _make_cutaway,
    _make_placeholder_staff,
    _sanitize_measure,
    get_parts_staff_elements,
)

logger = logging.getLogger(__name__)

_RENAME_FINGERPRINT_MEASURES = 5


@dataclass(frozen=True)
class StaffKey:
    """Stable identity for one score-level staff within a part."""

    part_name: str
    staff_index: int  # 0-based within the part

    def __str__(self) -> str:
        if self.staff_index:
            return f"{self.part_name}#{self.staff_index}"
        return self.part_name


class RowKind(Enum):
    MATCHED = "matched"
    RENAMED = "renamed"
    LEFT_ONLY = "left_only"
    RIGHT_ONLY = "right_only"


@dataclass
class AlignmentRow:
    kind: RowKind
    key_left: StaffKey | None
    key_right: StaffKey | None
    staff_left: ET.Element | None
    staff_right: ET.Element | None
    part_index_left: int | None
    part_index_right: int | None


@dataclass
class StaffAlignment:
    """Result of aligning score1 (left) to score2 (right)."""

    rows: list[AlignmentRow]

    @property
    def pair_count(self) -> int:
        return len(self.rows)

    def matched_pairs(self) -> list[tuple[ET.Element, ET.Element]]:
        return [
            (r.staff_left, r.staff_right)
            for r in self.rows
            if r.staff_left is not None
            and r.staff_right is not None
            and r.kind in (RowKind.MATCHED, RowKind.RENAMED)
        ]


def _staff_fingerprint(staff: ET.Element) -> str:
    hashes: list[str] = []
    for measure in staff.findall("Measure")[:_RENAME_FINGERPRINT_MEASURES]:
        hashes.append(_hash_measure(_sanitize_measure(measure)))
    return "|".join(hashes) if hashes else ""


def _part_fingerprint(staves: list[ET.Element]) -> str:
    return "::".join(_staff_fingerprint(s) for s in staves)


def _make_staff_key(part_name: str, staff_index: int) -> StaffKey:
    return StaffKey(part_name=part_name, staff_index=staff_index)


def align_staves(score1: ET.Element, score2: ET.Element) -> StaffAlignment:
    """
    Align parts and staves between two scores.

    score1 is the reference (left). Parts match on ``<trackName>`` first; unmatched
    parts may pair via content fingerprint (rename heuristic). Staves within a matched
    part pair in order; extra staves become ``LEFT_ONLY`` / ``RIGHT_ONLY`` rows.
    """
    parts1 = get_parts_staff_elements(score1)
    parts2 = get_parts_staff_elements(score2)

    pool2: deque[int] = deque(range(len(parts2)))
    unmatched1: list[int] = []
    part_pairings: list[tuple[int, int, bool]] = []

    for idx1, (name1, _) in enumerate(parts1):
        found = None
        for pos, idx2 in enumerate(pool2):
            name2, _ = parts2[idx2]
            if name2 == name1:
                found = (pos, idx2)
                break
        if found is None:
            unmatched1.append(idx1)
            continue
        pos, idx2 = found
        for _ in range(pos):
            pool2.popleft()
        pool2.popleft()
        part_pairings.append((idx1, idx2, False))

    unmatched2 = list(pool2)

    used2: set[int] = set()
    rename_pairings: list[tuple[int, int]] = []
    for idx1 in list(unmatched1):
        fp1 = _part_fingerprint(parts1[idx1][1])
        if not fp1:
            continue
        for idx2 in unmatched2:
            if idx2 in used2:
                continue
            fp2 = _part_fingerprint(parts2[idx2][1])
            if fp1 == fp2:
                rename_pairings.append((idx1, idx2))
                used2.add(idx2)
                unmatched1.remove(idx1)
                break

    for idx1, idx2 in rename_pairings:
        part_pairings.append((idx1, idx2, True))
        unmatched2 = [i for i in unmatched2 if i != idx2]
        name1, name2 = parts1[idx1][0], parts2[idx2][0]
        logger.info("Aligned renamed part %r -> %r", name1, name2)

    rows: list[AlignmentRow] = []

    def _append_staff_rows(
        kind: RowKind,
        name1: str,
        staves1: list[ET.Element],
        name2: str,
        staves2: list[ET.Element],
        idx1: int | None,
        idx2: int | None,
    ) -> None:
        for si in range(max(len(staves1), len(staves2))):
            s1 = staves1[si] if si < len(staves1) else None
            s2 = staves2[si] if si < len(staves2) else None
            if s1 is not None and s2 is not None:
                rows.append(
                    AlignmentRow(
                        kind=kind,
                        key_left=_make_staff_key(name1, si),
                        key_right=_make_staff_key(name2, si),
                        staff_left=s1,
                        staff_right=s2,
                        part_index_left=idx1,
                        part_index_right=idx2,
                    )
                )
            elif s1 is not None:
                rows.append(
                    AlignmentRow(
                        kind=RowKind.LEFT_ONLY,
                        key_left=_make_staff_key(name1, si),
                        key_right=None,
                        staff_left=s1,
                        staff_right=None,
                        part_index_left=idx1,
                        part_index_right=None,
                    )
                )
            else:
                rows.append(
                    AlignmentRow(
                        kind=RowKind.RIGHT_ONLY,
                        key_left=None,
                        key_right=_make_staff_key(name2, si),
                        staff_left=None,
                        staff_right=s2,
                        part_index_left=None,
                        part_index_right=idx2,
                    )
                )

    for idx1, idx2, renamed in sorted(part_pairings, key=lambda t: (t[0], t[1])):
        name1, staves1 = parts1[idx1]
        name2, staves2 = parts2[idx2]
        kind = RowKind.RENAMED if renamed else RowKind.MATCHED
        _append_staff_rows(kind, name1, staves1, name2, staves2, idx1, idx2)

    for idx1 in unmatched1:
        name1, staves1 = parts1[idx1]
        for si, s1 in enumerate(staves1):
            rows.append(
                AlignmentRow(
                    kind=RowKind.LEFT_ONLY,
                    key_left=_make_staff_key(name1, si),
                    key_right=None,
                    staff_left=s1,
                    staff_right=None,
                    part_index_left=idx1,
                    part_index_right=None,
                )
            )

    for idx2 in unmatched2:
        name2, staves2 = parts2[idx2]
        for si, s2 in enumerate(staves2):
            rows.append(
                AlignmentRow(
                    kind=RowKind.RIGHT_ONLY,
                    key_left=None,
                    key_right=_make_staff_key(name2, si),
                    staff_left=None,
                    staff_right=s2,
                    part_index_left=None,
                    part_index_right=idx2,
                )
            )

    return StaffAlignment(rows=rows)


def build_union_from_alignment(
    score1: ET.Element,
    score2: ET.Element,
    alignment: StaffAlignment,
    *,
    rhs_label_suffix: str = "-1",
) -> tuple[list[ET.Element], list[ET.Element], list[str]]:
    """Build interleaved Part/Staff lists for unified diff display."""
    part_elems1 = score1.findall("Part")
    part_elems2 = score2.findall("Part")
    parts1 = get_parts_staff_elements(score1)
    parts2 = get_parts_staff_elements(score2)

    union_parts: list[ET.Element] = []
    union_staves: list[ET.Element] = []
    part_names: list[str] = []

    def _set_track_name(part: ET.Element, name: str) -> None:
        track = part.find("trackName")
        if track is not None:
            track.text = name

    def _take_group(kind: RowKind) -> list[AlignmentRow]:
        nonlocal i
        group: list[AlignmentRow] = []
        while i < len(alignment.rows) and alignment.rows[i].kind == kind:
            group.append(alignment.rows[i])
            i += 1
        return group

    i = 0
    while i < len(alignment.rows):
        row = alignment.rows[i]

        if row.kind == RowKind.LEFT_ONLY:
            group = _take_group(RowKind.LEFT_ONLY)
            idx = group[0].part_index_left
            assert idx is not None
            name = parts1[idx][0]
            union_parts.append(deepcopy(part_elems1[idx]))
            part_names.append(name)
            for r in group:
                union_staves.append(deepcopy(r.staff_left))
            p_rhs = deepcopy(part_elems1[idx])
            _set_track_name(p_rhs, f"{name}{rhs_label_suffix}")
            union_parts.append(p_rhs)
            part_names.append(f"{name}{rhs_label_suffix}")
            for r in group:
                union_staves.append(_make_placeholder_staff(r.staff_left))
            continue

        if row.kind == RowKind.RIGHT_ONLY:
            group = _take_group(RowKind.RIGHT_ONLY)
            idx = group[0].part_index_right
            assert idx is not None
            name = parts2[idx][0]
            ref = group[0].staff_right
            assert ref is not None
            p_lhs = deepcopy(part_elems2[idx])
            _set_track_name(p_lhs, name)
            union_parts.append(p_lhs)
            part_names.append(name)
            for r in group:
                union_staves.append(_make_placeholder_staff(r.staff_right))
            p_rhs = deepcopy(part_elems2[idx])
            _set_track_name(p_rhs, f"{name}{rhs_label_suffix}")
            union_parts.append(p_rhs)
            part_names.append(f"{name}{rhs_label_suffix}")
            for r in group:
                sc = deepcopy(r.staff_right)
                sc.append(_make_cutaway())
                union_staves.append(sc)
            continue

        if row.kind in (RowKind.MATCHED, RowKind.RENAMED):
            group: list[AlignmentRow] = []
            while i < len(alignment.rows) and alignment.rows[i].kind in (
                RowKind.MATCHED,
                RowKind.RENAMED,
            ):
                group.append(alignment.rows[i])
                i += 1
            idx_l = group[0].part_index_left
            idx_r = group[0].part_index_right
            assert idx_l is not None and idx_r is not None
            name_l = parts1[idx_l][0]
            name_r = parts2[idx_r][0]
            union_parts.append(deepcopy(part_elems1[idx_l]))
            part_names.append(name_l)
            for r in group:
                union_staves.append(deepcopy(r.staff_left))
            rhs_label = (
                f"{name_r}{rhs_label_suffix}"
                if group[0].kind == RowKind.RENAMED
                else f"{name_l}{rhs_label_suffix}"
            )
            union_parts.append(deepcopy(part_elems2[idx_r]))
            _set_track_name(union_parts[-1], rhs_label)
            part_names.append(rhs_label)
            for r in group:
                if r.staff_right is not None:
                    sc = deepcopy(r.staff_right)
                    sc.append(_make_cutaway())
                    union_staves.append(sc)
            continue

        i += 1

    stub_count = sum(len(p.findall("Staff")) for p in union_parts)
    if stub_count != len(union_staves):
        raise ValueError(
            f"Union layout mismatch: {stub_count} part stubs vs {len(union_staves)} staves"
        )
    return union_parts, union_staves, part_names

