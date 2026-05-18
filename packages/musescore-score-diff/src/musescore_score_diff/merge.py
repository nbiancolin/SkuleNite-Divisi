import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from musescore_score_diff.display_diff import compare_musescore_files
from musescore_score_diff.compute_diff import compute_diff
from musescore_score_diff.utils import State, get_staves


class ComplicatedMergeException(Exception):
    pass

class MergeConflictException(Exception):
    pass


def find_merge_conflicts(
    base_to_head: dict[int, dict[int, State]],
    base_to_user: dict[int, dict[int, State]],
) -> dict[int, dict[int, State]]:
    """Measures where head and user both changed the same index relative to base."""
    res: dict[int, dict[int, State]] = {}
    for staff_id in base_to_head:
        head_states = base_to_head[staff_id]
        user_states = base_to_user[staff_id]
        measures = set(head_states) | set(user_states)
        conflicts: dict[int, State] = {}
        for measure_num in measures:
            head_state = head_states.get(measure_num, State.UNCHANGED)
            user_state = user_states.get(measure_num, State.UNCHANGED)
            if head_state == State.UNCHANGED or user_state == State.UNCHANGED:
                continue
            if head_state == State.MODIFIED and user_state == State.MODIFIED:
                conflicts[measure_num] = head_state
            elif head_state != user_state:
                conflicts[measure_num] = head_state
        if conflicts:
            res[staff_id] = conflicts
    return res


def three_way_merge_mscz(base_mscz_path, head_mscz_path, user_mscz_path, output_mscz_path) -> None:
    """
    Perform a 3 way merge on mscz files. For Divisi

    Tries to auto merge and write output to output_mscz_path.
    If a merge conflict is found, write the unified merge score (to be handled by the user) and raises MergeConflictException
    if a merge score cannot be generated, raises ComplicatedMergeException
    """
    def _mscx_arcnames(mscz_path: str) -> set[str]:
        with zipfile.ZipFile(mscz_path, "r") as zf:
            return {name for name in zf.namelist() if name.endswith(".mscx")}

    def _write_mscz_from_dir(source_dir: str, output_path: str) -> None:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    arcname = os.path.relpath(full_path, source_dir).replace(os.sep, "/")
                    zipf.write(full_path, arcname)

    base_arcs = sorted(_mscx_arcnames(base_mscz_path))
    head_arcs = sorted(_mscx_arcnames(head_mscz_path))
    user_arcs = sorted(_mscx_arcnames(user_mscz_path))

    if base_arcs == head_arcs == user_arcs:
        mscx_merge_plan = [(arc, arc, arc) for arc in base_arcs]
    elif len(base_arcs) == len(head_arcs) == len(user_arcs) == 1:
        mscx_merge_plan = [(base_arcs[0], head_arcs[0], user_arcs[0])]
    else:
        raise ComplicatedMergeException("MSCZ archives do not contain the same .mscx files")

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
            os.makedirs(extract_dirs[label], exist_ok=True)
            with zipfile.ZipFile(mscz_path, "r") as zip_ref:
                zip_ref.extractall(extract_dirs[label])

        shutil.copytree(extract_dirs["head"], output_dir)

        for base_arc, head_arc, user_arc in mscx_merge_plan:
            base_mscx = os.path.join(extract_dirs["base"], base_arc)
            head_mscx = os.path.join(extract_dirs["head"], head_arc)
            user_mscx = os.path.join(extract_dirs["user"], user_arc)
            output_mscx = os.path.join(output_dir, head_arc)

            for path in (base_mscx, head_mscx, user_mscx):
                if not os.path.isfile(path):
                    raise ComplicatedMergeException(
                        f"Missing {head_arc} after extracting MSCZ archives"
                    )

            out_parent = os.path.dirname(output_mscx)
            if out_parent:
                os.makedirs(out_parent, exist_ok=True)
            try:
                three_way_merge_musescore(base_mscx, head_mscx, user_mscx, output_mscx)
            except MergeConflictException as exc:
                merge_error = exc
            except ComplicatedMergeException as exc:
                if not isinstance(merge_error, MergeConflictException):
                    merge_error = exc

        _write_mscz_from_dir(output_dir, output_mscz_path)

    if merge_error is not None:
        raise merge_error


def three_way_merge_musescore(base_mscx_path, head_mscx_path, user_mscx_path, output_mscx_path) -> None:
    """
    INTERNAL
    Perform a 3 way merge on mscx files. For Divisi

    Tries to auto merge and write output to output_mscz_path.
    If a merge conflict is found, write the unified merge score (to be handled by the user) and raises MergeConflictException
    if a merge score cannot be generated, raises ComplicatedMergeException
    """


    # Check if there are merge conflicts

    try:
        base_2_head = compute_diff(base_mscx_path, head_mscx_path)
        base_2_user = compute_diff(base_mscx_path, user_mscx_path)
    except AssertionError:
        # Once I figure this out, can use this to handle these cases, but for now :(
        print("ERROR: Cannot currently merge musescore files with different num staves (yet)")
        raise ComplicatedMergeException
    
    
    conflicts = find_merge_conflicts(base_2_head, base_2_user)
    if conflicts:
        # Merge conflict!
        compare_musescore_files(head_mscx_path, user_mscx_path, output_mscx_path, unified_diff=True)
        raise MergeConflictException
    
    else:
        # auto merge musescore files
        #TODO: this
        try:
            auto_merge_musescore_files(head_mscx_path, user_mscx_path, output_mscx_path, base_2_head, base_2_user)
        except MergeConflictException:
            # Generate merge conflicyt score and re-raise
            compare_musescore_files(head_mscx_path, user_mscx_path, output_mscx_path, unified_diff=True)
            raise MergeConflictException

        pass



def merge_staff_pair(head_staff, user_staff, head_measures_to_mark, user_measures_to_mark):
    from .utils import make_highlight_end_empty_measure, _make_empty_measure, highlight_measure, State
    measures1 = list(head_staff.findall("Measure"))
    measures2 = list(user_staff.findall("Measure"))

    #1 is head, 2 is user

    # We do the merging in the user score -- assume that their formatting is intended
    m_processed = [] #m_processed == m2_processed

    m1_processed = []
    m2_processed = []
    # upper_bound = max(len(measures1), len(measures2))
    prev_measure_highlighted = False
    upper_bound = max(max(head_measures_to_mark), max(user_measures_to_mark)) + 1

    # If a measure is inserted / deleted in one and not the other,
    # will be out of sync.
    # in this case, increase the offset to keep them in check
    head_offset = 0
    user_offset = 0

    for i in range(1, upper_bound):
        #pop from m1 and m2, and add to m1/m2 pocessed
        m1 = measures1.pop(0)
        m2 = measures2.pop(0)

        m1_next = measures1[0] if measures1 else None
        m2_next = measures2[0] if measures2 else None

        head_state = head_measures_to_mark[i + head_offset]
        user_state = user_measures_to_mark[i + user_offset]

        match (head_state, user_state):
            case (State.UNCHANGED, State.UNCHANGED):
                #take from head
                m_processed.append(m1)
            case (State.MODIFIED, State.MODIFIED):
                # Merge conflict - should have been caught but i guess not ...
                raise MergeConflictException
            case (State.INSERTED, State.INSERTED):
                # Potential merge conflict
                # IN this case, we should be taking all the inserted measures from one score and then all the inserted measures form the other
                print("WARNING: Potential merge conflict, resolved by taking User's inserted measure")
                m_processed.append(m2)
            case (State.REMOVED, State.REMOVED):
                # Not a merge onflict if they both indepenently did this... don't add either
                pass
            case (a, b) if (a == State.INSERTED) != (b == State.INSERTED):
                # Only one of them is added, so add both measure
                if head_state == State.INSERTED:
                    m_processed.append(m1)
                    user_offset -= 1
                    measures2.insert(0, m2)
                else:
                    m_processed.append(m2)
                    head_offset -= 1
                    measures1.insert(0, m1)
            
            case (State.UNCHANGED, State.MODIFIED):
                # take from user
                m_processed.append(m2)
            case (State.MODIFIED, State.UNCHANGED):
                #take from head
                m_processed.append(m1)

            case (State.UNCHANGED, State.REMOVED):
                #don't do anything
                measures2.insert(0, m2)
                pass
            case (State.REMOVED, State.UNCHANGED):
                # do nothing
                measures1.insert(0, m1)
                pass
            case _:
                raise AssertionError(
                    f"Unknown case encountered !!! This is very bad\nHead State: {head_state} User State: {user_state}"
                )
        
    
    
    #remove the old measures set
    for m2 in user_staff.findall("Measure"):
        user_staff.remove(m2)
    
    #add in all the new measures
    for m2 in m_processed:
        user_staff.append(m2)


def auto_merge_musescore_files(head_mscx_path: str, user_mscx_path: str, output_mscx_path: str, base_2_head, base_2_user):
    #Head staff
    parser = ET.XMLParser()
    head_tree = ET.parse(head_mscx_path, parser)
    root = head_tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    head_staves = score.findall("Staff")

    #User staff
    parser = ET.XMLParser()
    user_tree = ET.parse(user_mscx_path, parser)
    root = user_tree.getroot()
    score = root.find("Score")
    if score is None:
        raise ValueError("No <Score> tag found in the XML.")

    user_staves =  score.findall("Staff")

    for i, (head_staff, user_staff) in enumerate(zip(head_staves, user_staves)):
        staff_id = i + 1
        merge_staff_pair(head_staff, user_staff, base_2_head[staff_id], base_2_user[staff_id])

    # Output user tree to new path
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

