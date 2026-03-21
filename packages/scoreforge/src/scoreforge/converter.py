from __future__ import annotations

import xml.etree.ElementTree as ET
from fractions import Fraction

from scoreforge.models import (
    Annotation,
    BarLineType,
    Chord,
    Duration,
    Dynamic,
    InstrumentChange,
    MeasureRepeat,
    NoteHeadType,
    RehearsalMark,
    Rest,
    Score,
    SpannerEvent,
    StaffText,
)

_DURATION_TYPE_FROM_FRACTION = {
    Fraction(4, 1): "long",
    Fraction(2, 1): "breve",
    Fraction(1, 1): "whole",
    Fraction(1, 2): "half",
    Fraction(1, 4): "quarter",
    Fraction(1, 8): "eighth",
    Fraction(1, 16): "16th",
    Fraction(1, 32): "32nd",
    Fraction(1, 64): "64th",
    Fraction(1, 128): "128th",
    Fraction(1, 256): "256th",
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
    name, octave = pitch[:-1], int(pitch[-1])
    names = {
        "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11
    }
    return (octave + 1) * 12 + names[name]


def _duration_to_mscx(duration: Duration) -> tuple[str, int]:
    if duration.is_measure_rest:
        return "measure", 0
    value = duration.value
    if duration.tuplet_ratio:
        actual, normal = duration.tuplet_ratio
        value = value * Fraction(actual, normal)
    base = value
    for _ in range(duration.dots):
        base = base / Fraction(2) if base else base
    return _DURATION_TYPE_FROM_FRACTION.get(base, "quarter"), duration.dots


def _add_annotation(parent: ET.Element, annotation: Annotation) -> None:
    if isinstance(annotation, Dynamic):
        el = ET.SubElement(parent, "Dynamic")
        ET.SubElement(el, "subtype").text = annotation.subtype
        if annotation.velocity is not None:
            ET.SubElement(el, "velocity").text = str(annotation.velocity)
    elif isinstance(annotation, StaffText):
        el = ET.SubElement(parent, "StaffText")
        ET.SubElement(el, "text").text = annotation.text
    elif isinstance(annotation, RehearsalMark):
        el = ET.SubElement(parent, "RehearsalMark")
        ET.SubElement(el, "text").text = annotation.text
    elif isinstance(annotation, InstrumentChange):
        el = ET.SubElement(parent, "InstrumentChange")
        if annotation.label:
            ET.SubElement(el, "text").text = annotation.label
        ET.SubElement(el, "Instrument", id=annotation.instrument_id)


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

    ET.SubElement(score_el, "Division").text = str(score.division)
    md = score.metadata
    meta_tags = {
        "workTitle": md.title,
        "subtitle": md.subtitle,
        "composer": md.composer,
        "lyricist": md.lyricist,
        "arranger": md.arranger,
        "copyright": md.copyright,
    }
    for key, value in meta_tags.items():
        if value:
            el = ET.SubElement(score_el, "metaTag", name=key)
            el.text = value

    for part in score.parts:
        part_el = ET.SubElement(score_el, "Part", id=part.part_id)
        ET.SubElement(part_el, "trackName").text = part.name
        ET.SubElement(part_el, "Instrument", id=part.instrument_id)
        for staff in part.staves:
            ET.SubElement(part_el, "Staff", id=str(staff.staff_id))

    for part in score.parts:
        for staff in part.staves:
            staff_el = ET.SubElement(score_el, "Staff", id=str(staff.staff_id))
            for measure in staff.measures:
                measure_el = ET.SubElement(staff_el, "Measure")
                if measure.is_irregular:
                    ET.SubElement(measure_el, "irregular").text = "1"

                ordered_voices = sorted(measure.voices, key=lambda v: v.voice_index)
                for idx, voice in enumerate(ordered_voices):
                    voice_el = ET.SubElement(measure_el, "voice")
                    if idx == 0 and measure.key_sig is not None:
                        key_sig = ET.SubElement(voice_el, "KeySig")
                        ET.SubElement(key_sig, "concertKey").text = str(measure.key_sig.fifths)
                        if measure.key_sig.mode:
                            ET.SubElement(key_sig, "mode").text = measure.key_sig.mode
                    if idx == 0 and measure.time_sig is not None:
                        time_sig = ET.SubElement(voice_el, "TimeSig")
                        ET.SubElement(time_sig, "sigN").text = str(measure.time_sig.numerator)
                        ET.SubElement(time_sig, "sigD").text = str(measure.time_sig.denominator)
                    if idx == 0 and measure.tempo is not None:
                        tempo = ET.SubElement(voice_el, "Tempo")
                        ET.SubElement(tempo, "tempo").text = str(measure.tempo.bpm / 60.0)
                        if measure.tempo.text:
                            ET.SubElement(tempo, "text").text = measure.tempo.text

                    for event in voice.events:
                        if isinstance(event, Chord):
                            chord_el = ET.SubElement(voice_el, "Chord")
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(chord_el, "dots").text = str(dots)
                            ET.SubElement(chord_el, "durationType").text = duration_type
                            if event.no_stem:
                                ET.SubElement(chord_el, "noStem").text = "1"
                            for art in event.articulations:
                                art_el = ET.SubElement(chord_el, "Articulation")
                                ET.SubElement(art_el, "subtype").text = art
                            for note in event.notes:
                                note_el = ET.SubElement(chord_el, "Note")
                                ET.SubElement(note_el, "pitch").text = str(note.pitch)
                                ET.SubElement(note_el, "tpc").text = str(note.tpc)
                                if note.head != NoteHeadType.NORMAL:
                                    ET.SubElement(note_el, "head").text = note.head.value
                                if note.tie.has_tie_start:
                                    tie_start = ET.SubElement(note_el, "Spanner", type="Tie")
                                    ET.SubElement(tie_start, "next")
                                if note.tie.has_tie_end:
                                    tie_end = ET.SubElement(note_el, "Spanner", type="Tie")
                                    ET.SubElement(tie_end, "prev")
                                if note.parenthesised:
                                    sym_l = ET.SubElement(note_el, "Symbol")
                                    ET.SubElement(sym_l, "n").text = "noteheadParenthesisLeft"
                                    sym_r = ET.SubElement(note_el, "Symbol")
                                    ET.SubElement(sym_r, "n").text = "noteheadParenthesisRight"
                        elif isinstance(event, Rest):
                            rest_el = ET.SubElement(voice_el, "Rest")
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(rest_el, "dots").text = str(dots)
                            ET.SubElement(rest_el, "durationType").text = duration_type
                        elif isinstance(event, MeasureRepeat):
                            mr_el = ET.SubElement(voice_el, "MeasureRepeat")
                            ET.SubElement(mr_el, "subtype").text = str(event.count)
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(mr_el, "dots").text = str(dots)
                            ET.SubElement(mr_el, "durationType").text = duration_type
                        elif isinstance(event, SpannerEvent):
                            sp = ET.SubElement(voice_el, "Spanner", type=event.kind.value)
                            if event.is_start:
                                ET.SubElement(sp, "next")
                            else:
                                ET.SubElement(sp, "prev")
                            if event.subtype:
                                inner = ET.SubElement(sp, event.kind.value)
                                ET.SubElement(inner, "subtype").text = event.subtype

                    if idx == 0 and measure.bar_line and measure.bar_line != BarLineType.NORMAL:
                        bl = ET.SubElement(voice_el, "BarLine")
                        ET.SubElement(bl, "subtype").text = measure.bar_line.value
                    if idx == 0:
                        for annotation in measure.annotations:
                            _add_annotation(voice_el, annotation)

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

    staff_map = {
        s.get("id"): s
        for s in score_el.findall("Staff")
        if s.get("id") is not None
    }

    for part in score.parts:
        for staff in part.staves:
            staff_id = str(staff.staff_id)
            staff_el = staff_map.get(staff_id)
            if staff_el is None:
                continue

            for measure in staff.measures:
                measure_el = ET.SubElement(staff_el, "Measure")
                if measure.is_irregular:
                    ET.SubElement(measure_el, "irregular").text = "1"

                ordered_voices = sorted(measure.voices, key=lambda v: v.voice_index)
                if not ordered_voices:
                    ET.SubElement(measure_el, "voice")
                    continue

                for idx, voice in enumerate(ordered_voices):
                    voice_el = ET.SubElement(measure_el, "voice")
                    if idx == 0 and measure.key_sig is not None:
                        key = ET.SubElement(voice_el, "KeySig")
                        ET.SubElement(key, "concertKey").text = str(measure.key_sig.fifths)
                        if measure.key_sig.mode:
                            ET.SubElement(key, "mode").text = measure.key_sig.mode
                    if idx == 0 and measure.time_sig is not None:
                        ts = ET.SubElement(voice_el, "TimeSig")
                        ET.SubElement(ts, "sigN").text = str(measure.time_sig.numerator)
                        ET.SubElement(ts, "sigD").text = str(measure.time_sig.denominator)
                    if idx == 0 and measure.tempo is not None:
                        tempo = ET.SubElement(voice_el, "Tempo")
                        ET.SubElement(tempo, "tempo").text = str(measure.tempo.bpm / 60.0)
                        if measure.tempo.text:
                            ET.SubElement(tempo, "text").text = measure.tempo.text

                    for event in voice.events:
                        if isinstance(event, Chord):
                            chord_el = ET.SubElement(voice_el, "Chord")
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(chord_el, "dots").text = str(dots)
                            ET.SubElement(chord_el, "durationType").text = duration_type
                            for note in event.notes:
                                note_el = ET.SubElement(chord_el, "Note")
                                ET.SubElement(note_el, "pitch").text = str(note.pitch)
                                ET.SubElement(note_el, "tpc").text = str(note.tpc)
                                if note.head != NoteHeadType.NORMAL:
                                    ET.SubElement(note_el, "head").text = note.head.value
                                if note.tie.has_tie_start:
                                    sp = ET.SubElement(note_el, "Spanner", type="Tie")
                                    ET.SubElement(sp, "next")
                                if note.tie.has_tie_end:
                                    sp = ET.SubElement(note_el, "Spanner", type="Tie")
                                    ET.SubElement(sp, "prev")
                        elif isinstance(event, Rest):
                            rest_el = ET.SubElement(voice_el, "Rest")
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(rest_el, "dots").text = str(dots)
                            ET.SubElement(rest_el, "durationType").text = duration_type
                        elif isinstance(event, MeasureRepeat):
                            mr_el = ET.SubElement(voice_el, "MeasureRepeat")
                            ET.SubElement(mr_el, "subtype").text = str(event.count)
                            duration_type, dots = _duration_to_mscx(event.duration)
                            if dots > 0:
                                ET.SubElement(mr_el, "dots").text = str(dots)
                            ET.SubElement(mr_el, "durationType").text = duration_type
                        elif isinstance(event, SpannerEvent):
                            sp = ET.SubElement(voice_el, "Spanner", type=event.kind.value)
                            if event.is_start:
                                ET.SubElement(sp, "next")
                            else:
                                ET.SubElement(sp, "prev")
                            if event.subtype:
                                inner = ET.SubElement(sp, event.kind.value)
                                ET.SubElement(inner, "subtype").text = event.subtype

                    if idx == 0 and measure.bar_line and measure.bar_line != BarLineType.NORMAL:
                        bl = ET.SubElement(voice_el, "BarLine")
                        ET.SubElement(bl, "subtype").text = measure.bar_line.value
                    if idx == 0:
                        for annotation in measure.annotations:
                            _add_annotation(voice_el, annotation)

    return ET.ElementTree(root)

