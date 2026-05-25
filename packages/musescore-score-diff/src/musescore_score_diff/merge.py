import logging
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace

from mscx_utils import (
    extract_mscz,
    load_score_element,
    mscx_arcnames,
    mscx_path_from_extract_dir,
    partition_mscx_arcs,
    remove_excerpts_from_mscz_dir,
    write_mscz_from_dir,
)

from musescore_score_diff.alignment import RowKind, StaffKey, align_staves
from musescore_score_diff.compute_diff import compute_diff, _ops_for_row
from musescore_score_diff.display_diff import compare_musescore_files, compare_mscz_files
from musescore_score_diff.utils import (
    State,
    _hash_measure,
    _sanitize_measure,
)

logger = logging.getLogger(__name__)


class ComplicatedMergeException(Exception):
    pass


@dataclass(frozen=True)
class MergeConflictDetail:
    """One incompatible head/user change during a three-way merge."""

    staff_id: int
    alignment_step: int
    head_state: State
    user_state: State
    staff_name: str | None = None
    head_measure_no: int | None = None
    user_measure_no: int | None = None
    mscx_path: str | None = None

    def describe(self) -> str:
        part = f"staff {self.staff_id}"
        if self.staff_name:
            part += f" ({self.staff_name!r})"
        measures = []
        if self.head_measure_no is not None:
            measures.append(f"head m.{self.head_measure_no}")
        if self.user_measure_no is not None:
            measures.append(f"user m.{self.user_measure_no}")
        measure_str = f", {', '.join(measures)}" if measures else ""
        file_str = f", file {self.mscx_path!r}" if self.mscx_path else ""
        return (
            f"{part}, alignment step {self.alignment_step}{measure_str}: "
            f"head={self.head_state.name}, user={self.user_state.name}{file_str}"
        )


class MergeConflictException(Exception):
    """Raised when head and user versions cannot be auto-merged."""

    def __init__(
        self,
        conflicts: list[MergeConflictDetail] | None = None,
        *,
        source_mscx: str | None = None,
    ) -> None:
        details = list(conflicts or [])
        if source_mscx is not None:
            details = [
                replace(d, mscx_path=d.mscx_path or source_mscx) for d in details
            ]
        self.conflicts = details
        self.source_mscx = source_mscx
        super().__init__(self._format_message())

    @classmethod
    def single(cls, detail: MergeConflictDetail) -> "MergeConflictException":
        return cls([detail], source_mscx=detail.mscx_path)

    def _format_message(self) -> str:
        if not self.conflicts:
            return "Merge conflict"
        lines = [f"Merge conflict ({len(self.conflicts)} location(s)):"]
        lines.extend(f"  - {c.describe()}" for c in self.conflicts)
        return "\n".join(lines)


def _partition_mscx_arcs(arcs: set[str]) -> tuple[str, set[str]]:
    try:
        return partition_mscx_arcs(arcs)
    except ValueError as exc:
        raise ComplicatedMergeException(str(exc)) from exc


def _build_mscx_merge_plan(
    base_arcs: set[str],
    head_arcs: set[str],
    user_arcs: set[str],
    *,
    merge_excerpts: bool,
) -> list[tuple[str, str, str]]:
    """
    Plan (base_arc, head_arc, user_arc) triples to three-way merge.

    Always merges the main score. Optionally merges excerpts when all three
    archives list the same excerpt .mscx paths.
    """
    base_main, base_excerpts = _partition_mscx_arcs(base_arcs)
    head_main, head_excerpts = _partition_mscx_arcs(head_arcs)
    user_main, user_excerpts = _partition_mscx_arcs(user_arcs)

    plan: list[tuple[str, str, str]] = [(base_main, head_main, user_main)]

    if merge_excerpts:
        plan.extend((arc, arc, arc) for arc in sorted(base_excerpts))

    return plan


def _write_merge_conflict_diff_mscz(
    head_mscz_path: str, user_mscz_path: str, output_mscz_path: str
) -> None:
    """Build one unified diff MSCZ from the head and user archives."""
    head_arcs = mscx_arcnames(head_mscz_path)
    user_arcs = mscx_arcnames(user_mscz_path)
    head_main, head_excerpts = _partition_mscx_arcs(head_arcs)
    user_main, user_excerpts = _partition_mscx_arcs(user_arcs)

    with tempfile.TemporaryDirectory() as work_dir:
        head_dir = os.path.join(work_dir, "head")
        user_dir = os.path.join(work_dir, "user")
        output_dir = os.path.join(work_dir, "output")

        for dest, mscz_path in ((head_dir, head_mscz_path), (user_dir, user_mscz_path)):
            extract_mscz(mscz_path, dest)

        shutil.copytree(head_dir, output_dir)

        head_mscx = mscx_path_from_extract_dir(head_dir, head_main)
        user_mscx = mscx_path_from_extract_dir(user_dir, user_main)
        output_mscx = mscx_path_from_extract_dir(output_dir, head_main)

        if not os.path.isfile(head_mscx) or not os.path.isfile(user_mscx):
            raise ComplicatedMergeException(
                "Cannot generate merge conflict diff: missing main score file"
            )

        compare_musescore_files(
            head_mscx, user_mscx, output_mscx, unified_diff=True
        )

        if head_excerpts != user_excerpts:
            remove_excerpts_from_mscz_dir(output_dir)

        write_mscz_from_dir(output_dir, output_mscz_path)


def _measures_equivalent(
    head_measure: ET.Element | None, user_measure: ET.Element | None
) -> bool:
    """True when both measures exist and have the same canonical content hash."""
    if head_measure is None or user_measure is None:
        return False
    head_hash = _hash_measure(_sanitize_measure(head_measure))
    user_hash = _hash_measure(_sanitize_measure(user_measure))
    return head_hash == user_hash


def base_diffs_by_staff_key(
    base_mscx_path: str, other_mscx_path: str
) -> dict[StaffKey, list[State]]:
    """Measure edit scripts from base to other, keyed by base staff identity."""
    base = load_score_element(base_mscx_path)
    other = load_score_element(other_mscx_path)
    alignment = align_staves(base, other)
    by_key: dict[StaffKey, list[State]] = {}
    for row in alignment.rows:
        key = row.key_left if row.key_left is not None else row.key_right
        if key is not None:
            by_key[key] = _ops_for_row(row)
    return by_key


def _unchanged_ops_for_staff(staff: ET.Element) -> list[State]:
    return [State.UNCHANGED] * len(staff.findall("Measure"))


def find_merge_conflicts(
    base_to_head: dict[StaffKey, list[State]],
    base_to_user: dict[StaffKey, list[State]],
    *,
    head_staves: dict[StaffKey, ET.Element] | None = None,
    user_staves: dict[StaffKey, ET.Element] | None = None,
) -> dict[StaffKey, dict[int, State]]:
    """Alignment steps where head and user both changed relative to base incompatibly."""
    res: dict[StaffKey, dict[int, State]] = {}
    for key in set(base_to_head) | set(base_to_user):
        head_ops = base_to_head.get(key, [])
        user_ops = base_to_user.get(key, [])
        conflicts: dict[int, State] = {}
        head_staff = (head_staves or {}).get(key)
        user_staff = (user_staves or {}).get(key)
        measures1 = (
            list(head_staff.findall("Measure")) if head_staff is not None else None
        )
        measures2 = (
            list(user_staff.findall("Measure")) if user_staff is not None else None
        )
        for step, (head_state, user_state) in enumerate(
            zip(head_ops, user_ops), start=1
        ):
            m1 = measures1.pop(0) if measures1 else None
            m2 = measures2.pop(0) if measures2 else None
            if head_state == State.UNCHANGED or user_state == State.UNCHANGED:
                continue
            if head_state == State.MODIFIED and user_state == State.MODIFIED:
                if not _measures_equivalent(m1, m2):
                    conflicts[step] = head_state
            elif head_state != user_state:
                conflicts[step] = head_state
        if conflicts:
            res[key] = conflicts
    return res


def three_way_merge_mscz(base_mscz_path, head_mscz_path, user_mscz_path, output_mscz_path) -> None:
    """
    Perform a 3 way merge on mscz files. For Divisi

    Tries to auto merge and write output to output_mscz_path.
    If a merge conflict is found, write the unified merge score (to be handled by the user) and raises MergeConflictException
    if a merge score cannot be generated, raises ComplicatedMergeException
    """
    base_arcs = mscx_arcnames(base_mscz_path)
    head_arcs = mscx_arcnames(head_mscz_path)
    user_arcs = mscx_arcnames(user_mscz_path)

    head_main, _ = _partition_mscx_arcs(head_arcs)
    user_main, _ = _partition_mscx_arcs(user_arcs)
    _, base_excerpts = _partition_mscx_arcs(base_arcs)
    _, head_excerpts = _partition_mscx_arcs(head_arcs)
    _, user_excerpts = _partition_mscx_arcs(user_arcs)

    # Merge excerpts only when every archive has the same excerpt .mscx paths.
    merge_excerpts = base_excerpts == head_excerpts == user_excerpts and bool(
        base_excerpts
    )

    merge_error: Exception | None = None

    with tempfile.TemporaryDirectory() as work_dir:
        extract_dirs = {
            "base": os.path.join(work_dir, "base"),
            "head": os.path.join(work_dir, "head"),
            "user": os.path.join(work_dir, "user"),
        }
        output_dir = os.path.join(work_dir, "output")

        for label, mscz_path in (
            ("base", base_mscz_path),
            ("head", head_mscz_path),
            ("user", user_mscz_path),
        ):
            extract_mscz(mscz_path, extract_dirs[label])

        shutil.copytree(extract_dirs["user"], output_dir)

        mscx_merge_plan = _build_mscx_merge_plan(
            base_arcs, head_arcs, user_arcs, merge_excerpts=merge_excerpts
        )
        if not merge_excerpts:
            remove_excerpts_from_mscz_dir(output_dir)

        for base_arc, head_arc, user_arc in mscx_merge_plan:
            base_mscx = mscx_path_from_extract_dir(extract_dirs["base"], base_arc)
            head_mscx = mscx_path_from_extract_dir(extract_dirs["head"], head_arc)
            user_mscx = mscx_path_from_extract_dir(extract_dirs["user"], user_arc)
            output_mscx = mscx_path_from_extract_dir(output_dir, user_arc)

            for path in (base_mscx, head_mscx, user_mscx):
                if not os.path.isfile(path):
                    raise ComplicatedMergeException(
                        f"Missing {user_arc} after extracting MSCZ archives"
                    )

            out_parent = os.path.dirname(output_mscx)
            if out_parent:
                os.makedirs(out_parent, exist_ok=True)
            try:
                three_way_merge_musescore(
                    base_mscx,
                    head_mscx,
                    user_mscx,
                    output_mscx,
                    write_conflict_diff=False,
                    mscx_path=user_arc,
                )
            except MergeConflictException as exc:
                merge_error = MergeConflictException(
                    exc.conflicts, source_mscx=user_arc
                )
            except ComplicatedMergeException as exc:
                if not isinstance(merge_error, MergeConflictException):
                    merge_error = exc

        if isinstance(merge_error, MergeConflictException):
            head_mscx = mscx_path_from_extract_dir(extract_dirs["head"], head_main)
            user_mscx = mscx_path_from_extract_dir(extract_dirs["user"], user_main)
            head_user_diffs = compute_diff(head_mscx, user_mscx)
            compare_mscz_files(
                head_mscz_path,
                user_mscz_path,
                output_mscz_path,
                unified_diff=True,
                diffs=head_user_diffs,
            )
        else:
            write_mscz_from_dir(output_dir, output_mscz_path)

    if merge_error is not None:
        raise merge_error


def three_way_merge_musescore(
    base_mscx_path,
    head_mscx_path,
    user_mscx_path,
    output_mscx_path,
    *,
    write_conflict_diff: bool = True,
    mscx_path: str | None = None,
) -> None:
    """
    INTERNAL
    Perform a 3 way merge on mscx files. For Divisi

    Tries to auto merge and write output to output_mscz_path.
    If a merge conflict is found, write the unified merge score (to be handled by the user) and raises MergeConflictException
    if a merge score cannot be generated, raises ComplicatedMergeException
    """


    # Check if there are merge conflicts

    try:
        base_2_head = base_diffs_by_staff_key(base_mscx_path, head_mscx_path)
        base_2_user = base_diffs_by_staff_key(base_mscx_path, user_mscx_path)
    except ValueError as exc:
        logger.error("Cannot merge scores: %s", exc, exc_info=True)
        raise ComplicatedMergeException(str(exc)) from exc

    try:
        auto_merge_musescore_files(
            head_mscx_path,
            user_mscx_path,
            output_mscx_path,
            base_2_head,
            base_2_user,
            mscx_path=mscx_path or os.path.basename(head_mscx_path),
        )
    except MergeConflictException as exc:
        if write_conflict_diff:
            head_user_diffs = compute_diff(head_mscx_path, user_mscx_path)
            compare_musescore_files(
                head_mscx_path,
                user_mscx_path,
                output_mscx_path,
                unified_diff=True,
                diffs=head_user_diffs,
            )
        raise MergeConflictException(exc.conflicts, source_mscx=mscx_path) from exc



def merge_staff_pair(
    head_staff,
    user_staff,
    head_ops: list[State],
    user_ops: list[State],
    *,
    staff_id: int,
    staff_name: str | None = None,
    mscx_path: str | None = None,
) -> None:
    measures1 = list(head_staff.findall("Measure"))
    measures2 = list(user_staff.findall("Measure"))
    head_measure_total = len(measures1)
    user_measure_total = len(measures2)
    m_processed: list[ET.Element] = []
    max_steps = max(len(head_ops), len(user_ops))

    for step in range(max_steps):
        head_state = head_ops[step] if step < len(head_ops) else State.UNCHANGED
        user_state = user_ops[step] if step < len(user_ops) else State.UNCHANGED
        if not measures1 and not measures2:
            break

        head_measure_no = (
            head_measure_total - len(measures1) + 1 if measures1 else None
        )
        user_measure_no = (
            user_measure_total - len(measures2) + 1 if measures2 else None
        )
        m1 = measures1.pop(0) if measures1 else None
        m2 = measures2.pop(0) if measures2 else None
        alignment_step = step + 1

        match (head_state, user_state):
            case (State.UNCHANGED, State.UNCHANGED):
                if m1 is not None:
                    m_processed.append(m1)
            case (State.MODIFIED, State.MODIFIED):
                if _measures_equivalent(m1, m2):
                    if m2 is not None:
                        m_processed.append(m2)
                else:
                    raise MergeConflictException.single(
                        MergeConflictDetail(
                            staff_id=staff_id,
                            alignment_step=alignment_step,
                            head_state=head_state,
                            user_state=user_state,
                            staff_name=staff_name,
                            head_measure_no=head_measure_no,
                            user_measure_no=user_measure_no,
                            mscx_path=mscx_path,
                        )
                    )
            case (State.INSERTED, State.INSERTED):
                if _measures_equivalent(m1, m2):
                    if m2 is not None:
                        m_processed.append(m2)
                elif m2 is not None:
                    logger.warning(
                        "Staff %s alignment step %s: both sides inserted different "
                        "measures; keeping user's measure",
                        staff_id,
                        alignment_step,
                    )
                    m_processed.append(m2)
                elif m1 is not None:
                    m_processed.append(m1)
            case (State.REMOVED, State.REMOVED):
                pass
            case (a, b) if (a == State.INSERTED) != (b == State.INSERTED):
                if head_state == State.INSERTED:
                    if m1 is not None:
                        m_processed.append(m1)
                    if m2 is not None:
                        measures2.insert(0, m2)
                else:
                    if m2 is not None:
                        m_processed.append(m2)
                    if m1 is not None:
                        measures1.insert(0, m1)
            case (State.UNCHANGED, State.MODIFIED):
                if m2 is not None:
                    m_processed.append(m2)
            case (State.MODIFIED, State.UNCHANGED):
                if m1 is not None:
                    m_processed.append(m1)
            case (State.UNCHANGED, State.REMOVED):
                if m2 is not None:
                    measures2.insert(0, m2)
            case (State.REMOVED, State.UNCHANGED):
                if m1 is not None:
                    measures1.insert(0, m1)
            case _:
                raise AssertionError(
                    f"Unknown merge case: head={head_state} user={user_state}"
                )

    for m2 in user_staff.findall("Measure"):
        user_staff.remove(m2)
    for m2 in m_processed:
        user_staff.append(m2)


def auto_merge_musescore_files(
    head_mscx_path: str,
    user_mscx_path: str,
    output_mscx_path: str,
    base_2_head: dict[StaffKey, list[State]],
    base_2_user: dict[StaffKey, list[State]],
    *,
    mscx_path: str | None = None,
):
    head_tree = ET.parse(head_mscx_path)
    root = head_tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    user_tree = ET.parse(user_mscx_path)
    user_root = user_tree.getroot()
    user_score = user_root.find("Score")
    if user_score is None:
        raise ValueError("No <Score> tag found in the XML.")

    align_hu = align_staves(score, user_score)
    staff_id = 0
    for row in align_hu.rows:
        if row.kind not in (RowKind.MATCHED, RowKind.RENAMED):
            continue
        if row.staff_left is None or row.staff_right is None:
            continue
        key = row.key_left
        if key is None:
            continue
        staff_id += 1
        head_ops = base_2_head.get(key)
        user_ops = base_2_user.get(key)
        if head_ops is None:
            head_ops = _unchanged_ops_for_staff(row.staff_left)
        if user_ops is None:
            user_ops = _unchanged_ops_for_staff(row.staff_right)
        merge_staff_pair(
            row.staff_left,
            row.staff_right,
            head_ops,
            user_ops,
            staff_id=staff_id,
            staff_name=key.part_name,
            mscx_path=mscx_path,
        )

    user_tree.write(output_mscx_path, encoding="UTF-8", xml_declaration=True)


"""
Map out what the full score 3 way merge flow will look like:


Base Mscz: Reference point
Head Mscz: current head mscz, to merge user into
User Mscz: User's changes based on "Base" mscz


Compute diffs btwn Base-Head and Base-User.
If any diffs exist in both, we have a merge conflict:
-> Generate Unified Score Diff file

If no merge conflicts, we can perform auto merge:
- Start with header info in score
    - Map staff ids to their respective staff name (text)
    - if any staves from user don't exist in head, add them to head
        - ** important: don't do the same the other way ! **
    - Header complete (note that parts might get lost but we are not messing with parts)
        - DO NOT MESS WITH IDs: IDS shoud remain the same so as to not break parts. If you are adding a staff ID, add it to the bottom. the user can fix the layout issues themselves
    
- then onto staves
    - if a staff from user doesnt exist in head, add it to head's score and copy all measures over
    - go through diff for each staff:
        for each measure
            if state is UNCHANGED in both:
                - keep measure from head
            if state is MODIFIED for both:
                - merge conflict
            if state is ADDED for both:
                - keep measure from head   # NB: Potential merge conflict? could keep both, but not sure what to do here
            if state is ADDED for one but not the other:
                - add both (added, then append)
            if state is UNCHANGED in one, but MODIFIED in the other:
                - add modified measure
            if state is UNCHANGED in one, but DELETED in the other:
                - delete measure (don't add it)
            
"""

