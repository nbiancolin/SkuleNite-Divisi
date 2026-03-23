import xml.etree.ElementTree as ET
import re
from typing import Optional

from scoreforge.models import (
    Score,
    Note,
    Rest,
    Dynamic,
    MeasureRepeat,
    ChordGroup,
    ChordNote,
    Lyric,
    HairpinStart,
    HairpinEnd,
    OttavaStart,
    OttavaEnd,
    StaffText,
    RehearsalMark,
    ChordSymbol,
    Tempo,
    InstrumentChange,
    Event,
    SlurStart,
    SlurEnd,
    TieStart,
    TieEnd,
)
from scoreforge.mscx_util import json_to_element

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


def _append_lyric_xml(chord_el: ET.Element, lyric: Lyric) -> None:
    """Emit <Lyrics> under <Chord> (before <Note> children, MuseScore 4 style)."""
    ly = ET.SubElement(chord_el, "Lyrics")
    if lyric.syllabic is not None:
        ET.SubElement(ly, "syllabic").text = lyric.syllabic
    if lyric.verse is not None:
        ET.SubElement(ly, "no").text = str(lyric.verse)
    if lyric.ticks_f is not None:
        ET.SubElement(ly, "ticks_f").text = lyric.ticks_f
    ET.SubElement(ly, "text").text = lyric.text


def _append_chord_xml(
    parent_el: ET.Element,
    *,
    duration: float,
    dots: int,
    slur_start: Optional[SlurStart],
    slur_end: Optional[SlurEnd],
    stem_direction: Optional[str],
    no_stem: bool,
    articulations: tuple[str, ...],
    notes: list[ChordNote],
    lyrics: tuple[Lyric, ...] = (),
) -> None:
    """Emit one MuseScore <Chord> with one or more <Note> children."""
    chord = ET.SubElement(parent_el, "Chord")
    if dots > 0:
        ET.SubElement(chord, "dots").text = str(dots)
    ET.SubElement(chord, "durationType").text = DURATION_TYPE.get(duration, "quarter")

    for lyr in lyrics:
        _append_lyric_xml(chord, lyr)

    for sub in articulations:
        art = ET.SubElement(chord, "Articulation")
        ET.SubElement(art, "subtype").text = sub

    if stem_direction is not None:
        ET.SubElement(chord, "StemDirection").text = stem_direction
    if no_stem:
        ET.SubElement(chord, "noStem").text = "1"

    if slur_start is not None:
        spanner = ET.SubElement(chord, "Spanner", type="Slur")
        ET.SubElement(spanner, "Slur")
        next_el = ET.SubElement(spanner, "next")
        location_el = ET.SubElement(next_el, "location")
        ET.SubElement(location_el, "fractions").text = slur_start.next_fractions

    if slur_end is not None:
        spanner = ET.SubElement(chord, "Spanner", type="Slur")
        prev_el = ET.SubElement(spanner, "prev")
        location_el = ET.SubElement(prev_el, "location")
        ET.SubElement(location_el, "fractions").text = slur_end.prev_fractions

    for cn in notes:
        note_el = ET.SubElement(chord, "Note")
        for sym in cn.symbols:
            sym_el = ET.SubElement(note_el, "Symbol")
            ET.SubElement(sym_el, "name").text = sym
        ET.SubElement(note_el, "pitch").text = str(pitch_to_midi(cn.pitch))
        if cn.tpc is not None:
            ET.SubElement(note_el, "tpc").text = str(cn.tpc)
        if cn.head is not None:
            ET.SubElement(note_el, "head").text = cn.head
        if cn.play is not None:
            ET.SubElement(note_el, "play").text = "1" if cn.play else "0"
        if cn.fixed is not None:
            ET.SubElement(note_el, "fixed").text = "1" if cn.fixed else "0"
        if cn.fixed_line is not None:
            ET.SubElement(note_el, "fixedLine").text = str(cn.fixed_line)

        if cn.tie_start is not None:
            spanner = ET.SubElement(note_el, "Spanner", type="Tie")
            ET.SubElement(spanner, "Tie")
            next_el = ET.SubElement(spanner, "next")
            location_el = ET.SubElement(next_el, "location")
            if "/" in cn.tie_start.next_fractions:
                ET.SubElement(location_el, "fractions").text = cn.tie_start.next_fractions
            else:
                ET.SubElement(location_el, "measures").text = cn.tie_start.next_fractions

        if cn.tie_end is not None:
            spanner = ET.SubElement(note_el, "Spanner", type="Tie")
            prev_el = ET.SubElement(spanner, "prev")
            location_el = ET.SubElement(prev_el, "location")
            if "/" in cn.tie_end.prev_fractions:
                ET.SubElement(location_el, "fractions").text = cn.tie_end.prev_fractions
            else:
                ET.SubElement(location_el, "measures").text = cn.tie_end.prev_fractions


def _append_events_to_container(parent_el: ET.Element, events: list[Event]) -> None:
    """Write canonical events under a <voice> or minimal <Measure> container."""
    for event in events:
        if isinstance(event, Note):
            cn = ChordNote(
                pitch=event.pitch,
                tie_start=event.tie_start,
                tie_end=event.tie_end,
                tpc=event.tpc,
                symbols=event.symbols,
                head=event.head,
                play=event.play,
                fixed=event.fixed,
                fixed_line=event.fixed_line,
            )
            _append_chord_xml(
                parent_el,
                duration=event.duration,
                dots=event.dots,
                slur_start=event.slur_start,
                slur_end=event.slur_end,
                stem_direction=event.stem_direction,
                no_stem=event.no_stem,
                articulations=event.articulations,
                notes=[cn],
                lyrics=event.lyrics,
            )
        elif isinstance(event, ChordGroup):
            _append_chord_xml(
                parent_el,
                duration=event.duration,
                dots=event.dots,
                slur_start=event.slur_start,
                slur_end=event.slur_end,
                stem_direction=event.stem_direction,
                no_stem=event.no_stem,
                articulations=event.articulations,
                notes=list(event.notes),
                lyrics=event.lyrics,
            )
        elif isinstance(event, Rest):
            rest = ET.SubElement(parent_el, "Rest")
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
            dynamic_el = ET.SubElement(parent_el, "Dynamic")
            ET.SubElement(dynamic_el, "subtype").text = event.subtype
            if event.velocity is not None:
                ET.SubElement(dynamic_el, "velocity").text = str(event.velocity)
        elif isinstance(event, HairpinStart):
            spanner = ET.SubElement(parent_el, "Spanner", type="HairPin")
            hp = ET.SubElement(spanner, "HairPin")
            ET.SubElement(hp, "subtype").text = event.subtype
            if event.direction is not None:
                ET.SubElement(hp, "direction").text = event.direction
            next_el = ET.SubElement(spanner, "next")
            loc = ET.SubElement(next_el, "location")
            if event.next_measures is not None:
                ET.SubElement(loc, "measures").text = event.next_measures
            if event.next_fractions is not None:
                ET.SubElement(loc, "fractions").text = event.next_fractions
        elif isinstance(event, HairpinEnd):
            spanner = ET.SubElement(parent_el, "Spanner", type="HairPin")
            prev_el = ET.SubElement(spanner, "prev")
            loc = ET.SubElement(prev_el, "location")
            if event.prev_measures is not None:
                ET.SubElement(loc, "measures").text = event.prev_measures
            if event.prev_fractions is not None:
                ET.SubElement(loc, "fractions").text = event.prev_fractions
        elif isinstance(event, MeasureRepeat):
            mr_el = ET.SubElement(parent_el, "MeasureRepeat")
            ET.SubElement(mr_el, "subtype").text = event.subtype
            ET.SubElement(mr_el, "durationType").text = event.duration_type
            ET.SubElement(mr_el, "duration").text = event.duration
        elif isinstance(event, OttavaStart):
            spanner = ET.SubElement(parent_el, "Spanner", type="Ottava")
            ot = ET.SubElement(spanner, "Ottava")
            ET.SubElement(ot, "subtype").text = event.subtype
            next_el = ET.SubElement(spanner, "next")
            loc = ET.SubElement(next_el, "location")
            if event.next_measures is not None:
                ET.SubElement(loc, "measures").text = event.next_measures
            if event.next_fractions is not None:
                ET.SubElement(loc, "fractions").text = event.next_fractions
        elif isinstance(event, OttavaEnd):
            spanner = ET.SubElement(parent_el, "Spanner", type="Ottava")
            prev_el = ET.SubElement(spanner, "prev")
            loc = ET.SubElement(prev_el, "location")
            if event.prev_measures is not None:
                ET.SubElement(loc, "measures").text = event.prev_measures
            if event.prev_fractions is not None:
                ET.SubElement(loc, "fractions").text = event.prev_fractions
        elif isinstance(event, StaffText):
            st = ET.SubElement(parent_el, "StaffText")
            ET.SubElement(st, "text").text = event.text
        elif isinstance(event, RehearsalMark):
            rm = ET.SubElement(parent_el, "RehearsalMark")
            ET.SubElement(rm, "text").text = event.text
        elif isinstance(event, ChordSymbol):
            if event.xml:
                parent_el.append(ET.fromstring(event.xml))
        elif isinstance(event, Tempo):
            t_el = ET.SubElement(parent_el, "Tempo")
            ET.SubElement(t_el, "tempo").text = event.tempo
            if event.follow_text is not None:
                ET.SubElement(t_el, "followText").text = event.follow_text
            if event.text:
                t_el.append(ET.fromstring(event.text))
        elif isinstance(event, InstrumentChange):
            ic = ET.SubElement(parent_el, "InstrumentChange")
            if event.text:
                ET.SubElement(ic, "text").text = event.text
            if event.init is not None:
                ET.SubElement(ic, "init").text = str(event.init)
            ic.append(json_to_element(event.instrument_tree))


def _append_double_bar_line(voice_el: ET.Element) -> None:
    """MuseScore places end-of-bar double barlines inside the first <voice> (MS4 MSCX)."""
    bar = ET.SubElement(voice_el, "BarLine")
    ET.SubElement(bar, "subtype").text = "double"


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

            for lb in measure.layout_breaks:
                lb_el = ET.SubElement(measure_el, "LayoutBreak")
                ET.SubElement(lb_el, "subtype").text = lb.subtype

            vk_list = sorted(measure.voices.keys(), key=int) if measure.voices else ["0"]
            first_vk = vk_list[0]
            for vk in vk_list:
                voice_el = ET.SubElement(measure_el, "voice")
                _append_events_to_container(voice_el, measure.voices.get(vk, []))
                if measure.double_bar and vk == first_vk:
                    _append_double_bar_line(voice_el)

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

            for lb in measure.layout_breaks:
                lb_el = ET.SubElement(measure_el, "LayoutBreak")
                ET.SubElement(lb_el, "subtype").text = lb.subtype

            vk_list = sorted(measure.voices.keys(), key=int) if measure.voices else ["0"]
            for vi, vk in enumerate(vk_list):
                voice_el = ET.SubElement(measure_el, "voice")
                if vi == 0 and measure.key_sig is not None:
                    key_sig_el = ET.SubElement(voice_el, "KeySig")
                    if measure.key_sig.concert_key is not None:
                        ET.SubElement(key_sig_el, "concertKey").text = str(
                            measure.key_sig.concert_key
                        )
                    if measure.key_sig.custom is not None:
                        ET.SubElement(key_sig_el, "custom").text = str(
                            measure.key_sig.custom
                        )
                    if measure.key_sig.mode is not None:
                        ET.SubElement(key_sig_el, "mode").text = measure.key_sig.mode
                if vi == 0 and measure.time_sig is not None:
                    time_sig_el = ET.SubElement(voice_el, "TimeSig")
                    ET.SubElement(time_sig_el, "sigN").text = str(measure.time_sig.sig_n)
                    ET.SubElement(time_sig_el, "sigD").text = str(measure.time_sig.sig_d)
                _append_events_to_container(voice_el, measure.voices.get(vk, []))
                if vi == 0 and measure.double_bar:
                    _append_double_bar_line(voice_el)

    return ET.ElementTree(root)

