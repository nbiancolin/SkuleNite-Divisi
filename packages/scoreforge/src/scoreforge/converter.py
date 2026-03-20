import xml.etree.ElementTree as ET
import re

from scoreforge.models import Score, Note, Rest, Dynamic, MeasureRepeat

# Duration type mapping for MSCX format (canonical float -> MuseScore durationType)
DURATION_TYPE = {
    4: "whole",
    2: "half",
    1: "quarter",
    0.5: "eighth",
    0.25: "16th",
    0.125: "32nd",
    0.0625: "64th",
}



def midi_to_pitch(midi: int) -> str:
    """Convert MIDI note number to pitch string (e.g., 60 -> 'C4').
    
    Converts a MIDI note number to a pitch string representation used
    in the ScoreForge canonical format. Middle C (MIDI 60) becomes 'C4'.
    
    Args:
        midi: MIDI note number (0-127)
        
    Returns:
        Pitch string in format 'NoteOctave' (e.g., 'C4', 'C#4', 'Bb3')
        
    Example:
        >>> midi_to_pitch(60)
        'C4'
        >>> midi_to_pitch(61)
        'C#4'
    """
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[midi % 12]}{midi // 12 - 1}"


def pitch_to_midi(pitch: str) -> int:
    """Convert pitch string to MIDI note number (e.g., 'C4' -> 60).
    
    Converts a pitch string from the ScoreForge canonical format to a
    MIDI note number. This is the inverse of midi_to_pitch().
    
    Args:
        pitch: Pitch string in format 'NoteOctave' (e.g., 'C4', 'C#4', 'Bb3')
        
    Returns:
        MIDI note number (0-127)
        
    Example:
        >>> pitch_to_midi('C4')
        60
        >>> pitch_to_midi('C#4')
        61
    """
    # Accidental is only # or b; '-' before digits is a negative octave (not flat)
    match = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", pitch.strip())
    if match is None:
        raise ValueError(f"Invalid pitch format: {pitch!r}")

    letter, accidental, octave_str = match.groups()
    octave = int(octave_str)

    base_names = {
        "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11
    }
    semitone = base_names[letter.upper()]

    if accidental == "#":
        semitone += 1
    elif accidental in {"b", "-"}:
        semitone -= 1

    return (octave + 1) * 12 + semitone


def score_to_mscx(score: Score) -> ET.ElementTree:
    """Convert a Score object to an MSCX XML ElementTree.
    
    Creates a minimal MSCX XML structure from a Score object. This creates
    a basic MuseScore file with musical content but minimal metadata.
    For preserving full metadata, use merge_measures_into_template() instead.
    
    Args:
        score: Score object to convert
        
    Returns:
        ElementTree representing the MSCX format, ready to be written
        to a file using write_mscz()
        
    Note:
        This creates a minimal MSCX file. To preserve all metadata from
        an original file, use the template-based workflow with
        merge_measures_into_template() and write_mscz_from_template().
        
    Example:
        >>> from scoreforge.serialization import load_score_from_json
        >>> from scoreforge.io import write_mscz
        >>> from pathlib import Path
        >>> score = load_score_from_json(Path("score.json"))
        >>> tree = score_to_mscx(score)
        >>> write_mscz(tree, Path("output.mscz"))
    """
    root = ET.Element("museScore", version="4.0")
    score_el = ET.SubElement(root, "Score")

    for part in score.parts:
        part_el = ET.SubElement(score_el, "Part", id=part.part_id)

        for measure in part.measures:
            if measure.measure_len is not None:
                measure_el = ET.SubElement(
                    part_el, "Measure", attrib={"len": measure.measure_len}
                )
                ET.SubElement(measure_el, "irregular").text = "1"
            else:
                measure_el = ET.SubElement(part_el, "Measure")

            if measure.measure_repeat_count is not None:
                ET.SubElement(measure_el, "measureRepeatCount").text = str(
                    measure.measure_repeat_count
                )

            for event in measure.events:
                if isinstance(event, Note):
                    chord = ET.SubElement(measure_el, "Chord")
                    ET.SubElement(chord, "durationType").text = DURATION_TYPE.get(
                        event.duration, "quarter"
                    )

                    note_el = ET.SubElement(chord, "Note")
                    ET.SubElement(note_el, "pitch").text = str(
                        pitch_to_midi(event.pitch)
                    )

                elif isinstance(event, Rest):
                    rest = ET.SubElement(measure_el, "Rest")
                    if event.measure_duration is not None:
                        ET.SubElement(rest, "durationType").text = "measure"
                        ET.SubElement(rest, "duration").text = event.measure_duration
                    else:
                        ET.SubElement(rest, "durationType").text = DURATION_TYPE.get(
                            event.duration, "quarter"
                        )

    return ET.ElementTree(root)


def merge_measures_into_template(template_tree: ET.ElementTree, score: Score) -> ET.ElementTree:
    """Merge measures from a Score object into a template MSCX ElementTree.
    
    This function takes a template MSCX (with measures removed) and inserts
    the measures from the Score object into the appropriate Staff elements.
    
    Args:
        template_tree: ElementTree of the template MSCX (without measures)
        score: Score object containing the measures to insert
        
    Returns:
        ElementTree with measures merged into the template
    """
    root = template_tree.getroot()
    score_el = root.find("Score")
    
    if score_el is None:
        raise ValueError("Template MSCX does not contain a Score element")
    
    # Create a mapping of part_id to Staff elements
    staff_map = {}
    for staff_el in score_el.findall(".//Staff"):
        staff_id = staff_el.get("id")
        if staff_id:
            staff_map[staff_id] = staff_el
    
    # For each part in the score, find the matching staff and add measures
    for part in score.parts:
        staff_el = staff_map.get(part.part_id)
        if staff_el is None:
            # If staff not found, skip this part (or could create it, but that's more complex)
            # Try to find by string conversion (sometimes IDs are stored as strings vs ints)
            staff_el = staff_map.get(str(part.part_id))
            if staff_el is None:
                continue
        
        # Add measures to the staff
        for measure in part.measures:
            # Create Measure element with len attribute when measure has non-standard length
            if measure.measure_len is not None:
                measure_el = ET.SubElement(
                    staff_el, "Measure", attrib={"len": measure.measure_len}
                )
                ET.SubElement(measure_el, "irregular").text = "1"
            else:
                measure_el = ET.SubElement(staff_el, "Measure")
                if measure.irregular is not None:
                    ET.SubElement(measure_el, "irregular").text = str(measure.irregular)

            if measure.measure_repeat_count is not None:
                ET.SubElement(measure_el, "measureRepeatCount").text = str(
                    measure.measure_repeat_count
                )

            voice_el = ET.SubElement(measure_el, "voice")
            
            # Add KeySig if present (inside voice, before events)
            if measure.key_sig is not None:
                key_sig_el = ET.SubElement(voice_el, "KeySig")
                ET.SubElement(key_sig_el, "concertKey").text = str(measure.key_sig.concert_key)
            
            # Add TimeSig if present (inside voice, before events)
            if measure.time_sig is not None:
                time_sig_el = ET.SubElement(voice_el, "TimeSig")
                ET.SubElement(time_sig_el, "sigN").text = str(measure.time_sig.sig_n)
                ET.SubElement(time_sig_el, "sigD").text = str(measure.time_sig.sig_d)
            
            # Add events to the voice
            for event in measure.events:
                if isinstance(event, Note):
                    chord = ET.SubElement(voice_el, "Chord")
                    # Write dots before durationType to match MuseScore XML structure
                    if event.dots > 0:
                        ET.SubElement(chord, "dots").text = str(event.dots)
                    ET.SubElement(chord, "durationType").text = DURATION_TYPE.get(
                        event.duration, "quarter"
                    )
                    
                    # Write slur spanner on Chord if present
                    if event.slur_start is not None:
                        spanner = ET.SubElement(chord, "Spanner", type="Slur")
                        slur_el = ET.SubElement(spanner, "Slur")
                        next_el = ET.SubElement(spanner, "next")
                        location_el = ET.SubElement(next_el, "location")
                        ET.SubElement(location_el, "fractions").text = event.slur_start.next_fractions
                    
                    if event.slur_end is not None:
                        # For slur end, don't include Slur element - only prev element
                        spanner = ET.SubElement(chord, "Spanner", type="Slur")
                        prev_el = ET.SubElement(spanner, "prev")
                        location_el = ET.SubElement(prev_el, "location")
                        ET.SubElement(location_el, "fractions").text = event.slur_end.prev_fractions
                    
                    note_el = ET.SubElement(chord, "Note")
                    ET.SubElement(note_el, "pitch").text = str(
                        pitch_to_midi(event.pitch)
                    )
                    
                    # Write tie spanner on Note if present
                    if event.tie_start is not None:
                        spanner = ET.SubElement(note_el, "Spanner", type="Tie")
                        tie_el = ET.SubElement(spanner, "Tie")
                        next_el = ET.SubElement(spanner, "next")
                        location_el = ET.SubElement(next_el, "location")
                        # Check if it's a measure offset (just a number) or fractions (contains "/")
                        if "/" in event.tie_start.next_fractions:
                            ET.SubElement(location_el, "fractions").text = event.tie_start.next_fractions
                        else:
                            ET.SubElement(location_el, "measures").text = event.tie_start.next_fractions
                    
                    if event.tie_end is not None:
                        # For tie end, don't include Tie element - only prev element
                        spanner = ET.SubElement(note_el, "Spanner", type="Tie")
                        prev_el = ET.SubElement(spanner, "prev")
                        location_el = ET.SubElement(prev_el, "location")
                        # Check if it's a measure offset (just a number, possibly negative) or fractions (contains "/")
                        if "/" in event.tie_end.prev_fractions:
                            ET.SubElement(location_el, "fractions").text = event.tie_end.prev_fractions
                        else:
                            ET.SubElement(location_el, "measures").text = event.tie_end.prev_fractions
                
                elif isinstance(event, Rest):
                    rest = ET.SubElement(voice_el, "Rest")
                    # Write dots before durationType to match MuseScore XML structure
                    if event.dots > 0:
                        ET.SubElement(rest, "dots").text = str(event.dots)
                    if event.measure_duration is not None:
                        ET.SubElement(rest, "durationType").text = "measure"
                        ET.SubElement(rest, "duration").text = event.measure_duration
                    else:
                        ET.SubElement(rest, "durationType").text = DURATION_TYPE.get(
                            event.duration, "quarter"
                        )
                
                elif isinstance(event, Dynamic):
                    dynamic_el = ET.SubElement(voice_el, "Dynamic")
                    ET.SubElement(dynamic_el, "subtype").text = event.subtype

                elif isinstance(event, MeasureRepeat):
                    mr_el = ET.SubElement(voice_el, "MeasureRepeat")
                    ET.SubElement(mr_el, "subtype").text = event.subtype
                    ET.SubElement(mr_el, "durationType").text = event.duration_type
                    ET.SubElement(mr_el, "duration").text = event.duration
    
    return ET.ElementTree(root)

