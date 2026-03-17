import sys
import xml.etree.ElementTree as ET
import zipfile
import os
import shutil
from copy import deepcopy
from typing import List, Tuple
import tempfile

# Assuming these are imported from your utils
from .utils import extract_measures, State, _make_cutaway, _make_empty_measure, highlight_measure, make_highlight_end_empty_measure
from .compute_diff import compute_diff

def new_merge_musescore_files(f1_path, f2_path, output_path=None):
    """
    read in f1 and f2, create diff_score that is union of both scores

    make list of all parts in f1
    and all staves in f1
        Note that their IDs line up!

    make diff_score a deep_copy of score 1

    then, copy over all parts and scores from staff 2 into diff_score
    create list union_part_list and union_staff_list
    when adding a part to the part list:
        - simultaneously add the staff to the staff list
        - Need to insert it in the correct position
            - so, if the staff name exists in the list, name staff "<name>-1"
            - set all IDs by their position in the list afterwards,

    then, once lists are creatd
    overwrite all parts in diff_score with the parts (in order) from part_list
    and overwrite all staves in diff_score with the scores (in order) from score_list
    """
    tree1 = ET.parse(f1_path)
    tree2 = ET.parse(f2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    union_part_list = [part for part in score1.findall("Part")]
    part_names = [part.find("trackName").text for part in score1.findall("Part")]
    union_staff_list = [staff for staff in score1.findall("Staff")]

    def _make_cutaway() -> ET.Element:
        return ET.fromstring("<cutaway>1</cutaway>")

    for part, staff in zip(score2.findall("Part"), score2.findall("Staff")):
        # This assertion check only works for the score, not for parts !!
        # assert part.attrib["id"] == staff.attrib["id"], (
        #     f"ERROR: part id {part.attrib["id"]} not matching staff id {staff.attrib["id"]}"
        # )
        staff_name = part.find("trackName").text
        assert staff_name is not None
        try:
            index = part_names.index(staff_name)
            p = deepcopy(part)
            s = p.find("Staff")
            s.append(_make_cutaway())
            union_part_list.insert(index +1, p)
            part_names.insert(index +1, staff_name)
            union_staff_list.insert(index, deepcopy(staff))
        except ValueError:
            # append to end of list
            print(f"ValueError: {staff_name}")
            union_part_list.append(part)
            part_names.append(staff_name)
            union_staff_list.append(staff)
            continue
        #TODO: Piano staves get added wrong, should be added after the second staff, not the first staff
        

    diff_score_tree = deepcopy(tree1)

    # remove all parts, and add back all parts from union_part_list (update IDs as they are inserted)

    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")

    list_score = list(diff_score)
    part_first_index = -1
    staff_first_index = -1
    parts_to_delete = []
    for i in range(len(list_score)):
        elem = list_score[i]
        if elem.tag == "Part":
            if part_first_index == -1:
                part_first_index = i
            parts_to_delete.append(elem)
        if elem.tag == "Staff":
            if staff_first_index == -1:
                staff_first_index = i
            diff_score.remove(elem)
        
    assert part_first_index != -1, "Could not find any parts in diff-score..."
    assert staff_first_index != -1, "Could not find any staves in diff-score..."

    num_staves = len(union_staff_list)
    num_parts = len(union_part_list)
    # TODO: Something here is messing up -- drum staff not being copied correctly, eveyrhting works tho
    # assert num_staves == num_parts, f"Num staves: {num_staves}, num parts: {num_parts}\n {[staff.attrib['id'] for staff in union_staff_list]}\n{[staff.attrib['id'] for staff in union_part_list]}"
    #Why are there 11 staves? thats an odd umber ??

    # all staves removed, add back new staves 
    for staff in reversed(union_staff_list):
        staff.attrib["id"] = f"{num_staves}"
        num_staves -= 1
        diff_score.insert(staff_first_index, staff)

    #remove parts:
    for part in parts_to_delete:
        diff_score.remove(part)

    
    for part in reversed(union_part_list):
        part.attrib["id"] = f"{num_parts}"
        num_parts -= 1
        diff_score.insert(part_first_index, part)

    if output_path:
        diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    return (diff_score_tree, part_names)

def merge_musescore_files_for_diff(f1_path: str, f2_path: str) -> Tuple[ET.ElementTree, List[str]]:
    """
    Merge two MuseScore files for diff display (adapted from your new_merge_musescore_files).
    """
    tree1 = ET.parse(f1_path)
    tree2 = ET.parse(f2_path)

    root1 = tree1.getroot()
    root2 = tree2.getroot()

    score1 = root1.find("Score")
    score2 = root2.find("Score")
    if score1 is None or score2 is None:
        raise ValueError("Both files must contain a <Score> element.")

    # Get parts and create union lists
    union_part_list = [part for part in score1.findall("Part")]
    part_names = [part.find("trackName").text for part in score1.findall("Part")]
    union_staff_list = [staff for staff in score1.findall("Staff")]

    # Process parts from score2
    for part, staff in zip(score2.findall("Part"), score2.findall("Staff")):
        assert part.attrib["id"] == staff.attrib["id"], (
            "ERROR: Part and staff IDs got out of sync"
        )
        staff_name = part.find("trackName").text
        assert staff_name is not None
        
        try:
            index = part_names.index(staff_name)
            # Add "-1" suffix for diff version
            p = deepcopy(part)
            track_name_elem = p.find("trackName")
            if track_name_elem is not None:
                track_name_elem.text = f"{staff_name}-1"
            
            # Add cutaway for visual distinction
            s = deepcopy(staff)
            s.append(_make_cutaway())
            
            union_part_list.insert(index + 1, p)
            part_names.insert(index + 1, f"{staff_name}-1")
            union_staff_list.insert(index + 1, s)
        except ValueError:
            # Part doesn't exist in score1, append to end
            print(f"New part found: {staff_name}")
            p = deepcopy(part)
            track_name_elem = p.find("trackName")
            if track_name_elem is not None:
                track_name_elem.text = f"{staff_name}-1"
            
            union_part_list.append(p)
            part_names.append(f"{staff_name}-1")
            union_staff_list.append(deepcopy(staff))

    # Create diff score tree
    diff_score_tree = deepcopy(tree1)
    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")

    # Remove existing parts and staves
    list_score = list(diff_score)
    part_first_index = -1
    staff_first_index = -1
    parts_to_delete = []
    
    for i in range(len(list_score)):
        elem = list_score[i]
        if elem.tag == "Part":
            if part_first_index == -1:
                part_first_index = i
            parts_to_delete.append(elem)
        if elem.tag == "Staff":
            if staff_first_index == -1:
                staff_first_index = i
            diff_score.remove(elem)

    assert part_first_index != -1, "Could not find any parts in diff-score"
    assert staff_first_index != -1, "Could not find any staves in diff-score"

    # Add new staves with updated IDs
    num_staves = len(union_staff_list)
    for staff in reversed(union_staff_list):
        staff.attrib["id"] = f"{num_staves}"
        num_staves -= 1
        diff_score.insert(staff_first_index, staff)

    # Remove old parts
    for part in parts_to_delete:
        diff_score.remove(part)

    # Add new parts with updated IDs
    num_parts = len(union_part_list)
    for part in reversed(union_part_list):
        part.attrib["id"] = f"{num_parts}"
        num_parts -= 1
        diff_score.insert(part_first_index, part)

    return (diff_score_tree, part_names)

def mark_diffs_in_staff_pair(staff1, staff2, measures_to_mark) -> None:
    """
    Fn that goes through diff score, iterates over each staff.
    for each (staff, staff-1) pairing, and applies the selected diff
    if measure is unchanged, set the measure in staff-1 to be unchanged
        (NOTE: Potentially both? so it only shows the different measures) (maybe a toggleable option)
    if measure is modified, highlight staff red, and staff1 green
    if measure is added, add a measure of rest to staff, and highlight it red, highlight staff1 green
    if measure removed, add measue of rest to staff1, and highlight it in red, highlight staff red too

    """

    #process measures in a list so we can modify it, then add them all back afterwards
    measures1 = list(staff1.findall("Measure"))
    measures2 = list(staff2.findall("Measure"))

    m1_processed = []
    m2_processed = []
    # upper_bound = max(len(measures1), len(measures2))
    prev_measure_highlighted = False
    upper_bound = len(measures_to_mark.keys()) +1
    for i in range(1, upper_bound):
        #pop from m1 and m2, and add to m1/m2 pocessed
        m1 = measures1.pop(0)
        m2 = measures2.pop(0)

        m1_next = measures1[0] if measures1 else None
        m2_next = measures2[0] if measures2 else None
        match measures_to_mark[i]:
            case State.UNCHANGED:
                #clear staff2 (remove old measure)
                m1_processed.append(m1)
                if prev_measure_highlighted:
                    m2_processed.append(make_highlight_end_empty_measure())
                    prev_measure_highlighted = False
                else:
                    m2_processed.append(_make_empty_measure())
                # m2_processed.append(m2)   # <-- For testing
            case State.MODIFIED:
                #highlight staff1 red and staff2 green
                m1_processed.append(highlight_measure((200, 0, 0), m1, m1_next))
                m2_processed.append(highlight_measure((0, 200, 0), m2, m2_next))
                prev_measure_highlighted = True
                continue
            case State.INSERTED:
                #add measure of rest to staff1
                m1_processed.append(_make_empty_measure())
                measures1.insert(0, m1)
                #highlight staff green
                m2_processed.append(highlight_measure((0, 200, 0), m2, m2_next))
                continue
            case State.REMOVED:
                #add measure of rest to staff2, 
                m2_processed.append(_make_empty_measure())
                measures2.insert(0, m2)
                # highlight staff1 red
                m1_processed.append(highlight_measure((200, 0, 0), m1, m1_next))
                continue
        
    
    
    #remove the old measures set
    for m1 in staff1.findall("Measure"):
        staff1.remove(m1)

    for m2 in staff2.findall("Measure"):
        staff2.remove(m2)
    
    #add in all the new measures
    assert len(m1_processed) == len(m2_processed)
    for m1, m2 in zip(m1_processed, m2_processed):
        staff1.append(m1)
        staff2.append(m2)

def mark_diffs(diff_score, diffs) -> None:
    """
    Create staff pairs to be sent to `mark_diffs_in_staff_pair`
    
    """
    staves = diff_score.findall("Staff")
    i = 0
    j = 1
    while i < len(staves):
        if (i +1) >= len(staves):
            break
        mark_diffs_in_staff_pair(staves[i], staves[i +1], diffs[j])
        i += 2
        j += 1


def compare_musescore_files(file1_path: str, file2_path: str, output_path: str|None = None) -> str:
    """
    Main function to compare two MuseScore files and create a diff score.
    
    Args:
        file1_path: Path to the old version (score1)
        file2_path: Path to the new version (score2)
        output_path: Optional output path for the diff file
    
    Returns:
        Path to the generated diff file
    """
    # Generate output filename if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file1_path))[0]
        output_path = f"diff-{base_name}.mscx"

    print(f"Comparing {file1_path} and {file2_path}")
    
    # Create merged score with both versions
    diff_score_tree, part_names = new_merge_musescore_files(file1_path, file2_path)
    
    # Get the score element
    diff_root = diff_score_tree.getroot()
    diff_score = diff_root.find("Score")
    
    diffs = compute_diff(file1_path, file2_path)

    mark_diffs(diff_score, diffs)

    
    # Save the diff score
    diff_score_tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    
    print(f"Diff score saved as: {output_path}")
    return output_path

def compare_mscz_files(file1_path: str, file2_path: str, output_path: str|None = None) -> str:
    """
    Compare two .mscz files by extracting and processing their .mscx contents.

    Should only process the main mscx file, no parts
    """
    both_mscx_files = []

    with tempfile.TemporaryDirectory() as work_dir: 
        # Extract .mscx files from both .mscz files
        for input_path in [file1_path, file2_path]:
            
            with zipfile.ZipFile(input_path, "r") as zip_ref:
                zip_ref.extractall(work_dir)
                mscx_files = [
                    os.path.join(work_dir, f) for f in zip_ref.namelist() 
                    if f.endswith(".mscx")
                ]
            both_mscx_files.append(mscx_files)

        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(file1_path))[0]
            output_path = f"diff-{base_name}.mscz"

        # Process each .mscx file pair
        output_files = []
        for file1, file2 in zip(both_mscx_files[0], both_mscx_files[1]):
            mscx_output = file1.replace(os.path.basename(file1), f"diff-{os.path.basename(file1)}")
            compare_musescore_files(file1, file2, mscx_output)
            output_files.append(mscx_output)
            print(f"Processed: {os.path.basename(file1)}")

        # Create output .mscz file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for output_file in output_files:
                arcname = os.path.relpath(output_file, os.path.dirname(output_file))
                zipf.write(output_file, arcname)

    
    print(f"Diff .mscz file created: {output_path}")
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
        # Determine file type and process accordingly
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