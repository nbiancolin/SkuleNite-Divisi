import logging
import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from copy import deepcopy
from typing import List, Tuple
import tempfile

logger = logging.getLogger(__name__)

from .utils import (
    State,
    build_unified_diff_union,
    install_union_layout_into_score,
    highlight_measure,
    make_highlight_end_empty_measure,
    mscx_path_from_extract_dir,
    pick_main_mscx_arc_from_namelist,
    _make_empty_measure,
    _effective_measure_duration,
)
from .compute_diff import compute_diff


def merge_musescore_files_for_diff(f1_path: str, f2_path: str) -> Tuple[ET.ElementTree, List[str]]:
    """
    Merge two MuseScore files for unified diff display.

    Each part is followed by a duplicate part (``trackName`` + ``-1``) holding the
    second score's staves, with score-level staves interleaved and IDs kept in sync.
    """
    tree1 = ET.parse(f1_path)
    tree2 = ET.parse(f2_path)

    score1 = tree1.getroot().find("Score")
    score2 = tree2.getroot().find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    union_parts, union_staves, part_names = build_unified_diff_union(score1, score2)

    diff_score_tree = deepcopy(tree1)
    diff_score = diff_score_tree.getroot().find("Score")
    if diff_score is None:
        raise ValueError("Both files must contain a <Score> element.")

    install_union_layout_into_score(diff_score, union_parts, union_staves)
    return (diff_score_tree, part_names)


def new_merge_musescore_files(f1_path, f2_path, output_path=None):
    """Alias for unified diff merge (kept for compatibility)."""
    diff_score_tree, part_names = merge_musescore_files_for_diff(f1_path, f2_path)
    if output_path:
        diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    return (diff_score_tree, part_names)


def mark_diffs_in_staff_pair(staff1, staff2, ops: list[State], unified=True) -> None:
    """
    Apply an ordered edit script to a (staff, staff-1) pair in a unified diff score.
    """
    measures1 = list(staff1.findall("Measure"))
    measures2 = list(staff2.findall("Measure"))
    m1_processed: list[ET.Element] = []
    m2_processed: list[ET.Element] = []
    prev_measure_highlighted = False
    i1 = 0
    i2 = 0

    for state in ops:
        match state:
            case State.UNCHANGED:
                m1 = measures1[i1]
                m2 = measures2[i2]
                i1 += 1
                i2 += 1
                m1_processed.append(m1)
                duration = _effective_measure_duration(staff1, i1)
                if prev_measure_highlighted:
                    m2_processed.append(make_highlight_end_empty_measure(duration))
                    prev_measure_highlighted = False
                elif unified:
                    m2_processed.append(_make_empty_measure(duration))
                else:
                    m2_processed.append(m2)
            case State.MODIFIED:
                m1 = measures1[i1]
                m2 = measures2[i2]
                m1_next = measures1[i1 + 1] if i1 + 1 < len(measures1) else None
                m2_next = measures2[i2 + 1] if i2 + 1 < len(measures2) else None
                i1 += 1
                i2 += 1
                m1_processed.append(highlight_measure((200, 0, 0), m1, m1_next))
                m2_processed.append(highlight_measure((0, 200, 0), m2, m2_next))
                prev_measure_highlighted = True
            case State.INSERTED:
                m2 = measures2[i2]
                m2_next = measures2[i2 + 1] if i2 + 1 < len(measures2) else None
                i2 += 1
                m1_processed.append(_make_empty_measure())
                m2_processed.append(highlight_measure((0, 200, 0), m2, m2_next))
                prev_measure_highlighted = True
            case State.REMOVED:
                m1 = measures1[i1]
                m1_next = measures1[i1 + 1] if i1 + 1 < len(measures1) else None
                i1 += 1
                m2_processed.append(
                    _make_empty_measure(_effective_measure_duration(staff1, i1))
                )
                m1_processed.append(highlight_measure((200, 0, 0), m1, m1_next))
                prev_measure_highlighted = True

    if i1 != len(measures1) or i2 != len(measures2):
        raise ValueError(
            f"Edit script does not consume all measures "
            f"({i1}/{len(measures1)} left, {i2}/{len(measures2)} right)"
        )

    for m1 in staff1.findall("Measure"):
        staff1.remove(m1)
    for m2 in staff2.findall("Measure"):
        staff2.remove(m2)

    assert len(m1_processed) == len(m2_processed)
    for m1, m2 in zip(m1_processed, m2_processed):
        staff1.append(m1)
        staff2.append(m2)


def mark_diffs_separate(lhs_score: ET.Element, rhs_score: ET.Element, diffs) -> None:
    """Apply diffs to two parallel scores (non-unified display)."""
    lhs_staves, rhs_staves = lhs_score.findall("Staff"), rhs_score.findall("Staff")

    assert len(lhs_staves) == len(rhs_staves)

    j = 1
    for lhs_staff, rhs_staff in zip(lhs_staves, rhs_staves):
        mark_diffs_in_staff_pair(lhs_staff, rhs_staff, diffs[j], unified=False)
        j += 1


def mark_diffs_unified(diff_score, diffs) -> None:
    """Pair consecutive staves (LHS/RHS) and apply per-staff edit scripts."""
    staves = diff_score.findall("Staff")
    i = 0
    j = 1
    while i + 1 < len(staves):
        if j in diffs:
            mark_diffs_in_staff_pair(staves[i], staves[i + 1], diffs[j])
        i += 2
        j += 1


def compare_musescore_files(file1_path: str, file2_path: str, output_path: str|None = None, unified_diff: bool = True, diffs: dict | None = None) -> str:
    """
    Main function to compare two MuseScore files and create a diff score.
    
    Args:
        file1_path: Path to the old version (score1)
        file2_path: Path to the new version (score2)
        output_path: Optional output path for the diff file
        unified_diff: Optional: a method for displaying large diffs as 2 separate files instead of one unified
        diffs: DO NOT USE: for divisi, for overriding with custom diffs to mark / display
    
    Returns:
        Path to the generated diff file
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file1_path))[0]
        output_path = f"diff-{base_name}.mscx"

    logger.info("Comparing %s and %s", file1_path, file2_path)

    if unified_diff is True:
        diff_score_tree, _part_names = merge_musescore_files_for_diff(file1_path, file2_path)
        
        diff_root = diff_score_tree.getroot()
        diff_score = diff_root.find("Score")
        
        if not diffs:
            diffs = compute_diff(file1_path, file2_path)

        mark_diffs_unified(diff_score, diffs)

        diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
        
        logger.info("Diff score saved as: %s", output_path)
        return output_path
    
    else:
        tree1 = ET.parse(file1_path)
        tree2 = ET.parse(file2_path)

        root1 = tree1.getroot()
        root2 = tree2.getroot()

        score1 = root1.find("Score")
        score2 = root2.find("Score")

        if not diffs:
            diffs = compute_diff(file1_path, file2_path)
        mark_diffs_separate(score1, score2, diffs)

        lhs_output = f"{output_path}-lhs.mscx"
        tree1.write(lhs_output, encoding="UTF-8", xml_declaration=True)
        
        rhs_output = f"{output_path}-rhs.mscx"
        tree2.write(rhs_output, encoding="UTF-8", xml_declaration=True)


def _extract_mscz_main_mscx(mscz_path: str, extract_dir: str) -> tuple[str, str]:
    """Extract one .mscz into ``extract_dir`` and return (main arc, path on disk)."""
    with zipfile.ZipFile(mscz_path, "r") as zip_ref:
        namelist = zip_ref.namelist()
        main_arc = pick_main_mscx_arc_from_namelist(namelist)
        zip_ref.extractall(extract_dir)
    return main_arc, mscx_path_from_extract_dir(extract_dir, main_arc)


def compare_mscz_files(file1_path: str, file2_path: str, output_path: str|None = None, unified_diff: bool = True, diffs = None) -> str:
    """
    Compare two .mscz files by extracting and diffing each archive's main score .mscx.
    """
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file1_path))[0]
        output_path = f"diff-{base_name}.mscz"

    with tempfile.TemporaryDirectory() as work_dir:
        left_dir = os.path.join(work_dir, "left")
        right_dir = os.path.join(work_dir, "right")
        out_dir = os.path.join(work_dir, "out")
        os.makedirs(left_dir)
        os.makedirs(right_dir)
        os.makedirs(out_dir)

        left_arc, left_mscx = _extract_mscz_main_mscx(file1_path, left_dir)
        right_arc, right_mscx = _extract_mscz_main_mscx(file2_path, right_dir)

        if left_arc != right_arc:
            logger.warning(
                "Main score paths differ (%r vs %r); writing diff to %r",
                left_arc,
                right_arc,
                left_arc,
            )

        shutil.copytree(left_dir, out_dir, dirs_exist_ok=True)
        out_mscx = mscx_path_from_extract_dir(out_dir, left_arc)

        compare_musescore_files(
            left_mscx,
            right_mscx,
            out_mscx,
            unified_diff=unified_diff,
            diffs=diffs,
        )
        logger.debug("Processed main score: %s", left_arc)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(out_dir):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    arcname = os.path.relpath(full_path, out_dir).replace(os.sep, "/")
                    zipf.write(full_path, arcname)

    logger.info("Diff .mscz file created: %s", output_path)
    return output_path

def main():
    """Main function to run the diff comparison."""
    if len(sys.argv) not in [3, 4]:
        print("Usage: python musescore_diff.py <old_score> <new_score> [output_path]")
        print("Supports both .mscx and .mscz files")
        sys.exit(1)

    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) == 4 else file1_path

    if not os.path.exists(file1_path):
        print(f"Error: File {file1_path} not found")
        sys.exit(1)

    if not os.path.exists(file2_path):
        print(f"Error: File {file2_path} not found")
        sys.exit(1)

    try:
        if file1_path.endswith('.mscz') and file2_path.endswith('.mscz'):
            diff_file = compare_mscz_files(file1_path, file2_path, output_path)
        elif file1_path.endswith('.mscx') and file2_path.endswith('.mscx'):
            diff_file = compare_musescore_files(file1_path, file2_path, output_path)
        else:
            print("Error: Both files must be of the same type (.mscx or .mscz)")
            sys.exit(1)
            
        print(f"Successfully created diff file: {diff_file}")
    except Exception as e:
        print(f"Error creating diff: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
