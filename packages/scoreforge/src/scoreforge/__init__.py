"""ScoreForge - A tool for version controlling MuseScore files as text.

This package provides functionality to:
- Parse MuseScore files (MSCZ/MSCX) into a canonical JSON format
- Convert canonical JSON back to MuseScore files
- Merge multiple scores based on their canonical form
- Work with musical scores programmatically

Public API:
    Models:
        Score, Part, Measure, Note, Rest, Event, KeySig, TimeSig, Dynamic
    
    Parsing & Conversion:
        parse_score - Parse MSCX XML to Score object
        score_to_mscx - Convert Score object to MSCX XML
        extract_mscx - Extract MSCX from MSCZ archive
        write_mscz - Write MSCX ElementTree to MSCZ file
    
    Serialization:
        save_canonical - Save Score to canonical JSON format
        load_score_from_json - Load Score from canonical JSON format
    
    Merging:
        three_way_merge_scores - 3-way merge of base, head, and user scores
    
    Utilities:
        midi_to_pitch - Convert MIDI note number to pitch string
        pitch_to_midi - Convert pitch string to MIDI note number
"""

from scoreforge.models import (
    Annotation,
    BarLineType,
    Chord,
    Duration,
    Dynamic,
    InstrumentChange,
    KeySig,
    Measure,
    MeasureRepeat,
    Note,
    NoteHeadType,
    Part,
    RehearsalMark,
    Rest,
    Score,
    ScoreMetadata,
    SpannerEvent,
    SpannerKind,
    Staff,
    StaffText,
    Tempo,
    TieInfo,
    TimeSig,
    Voice,
    VoiceEvent,
)
from scoreforge.parser import canonical_hash, canonical_json, parse_mscx, parse_score
from scoreforge.converter import score_to_mscx, midi_to_pitch, pitch_to_midi
from scoreforge.io import extract_mscx, write_mscz
from scoreforge.serialization import save_canonical, load_score_from_json
from scoreforge.merger import MergeConflict, three_way_merge_scores

__version__ = "0.1.0"
__all__ = [
    # Models
    "Score",
    "Part",
    "Staff",
    "Measure",
    "Voice",
    "VoiceEvent",
    "Chord",
    "Note",
    "Rest",
    "MeasureRepeat",
    "SpannerEvent",
    "SpannerKind",
    "Annotation",
    "KeySig",
    "TimeSig",
    "Tempo",
    "Duration",
    "TieInfo",
    "NoteHeadType",
    "BarLineType",
    "Dynamic",
    "StaffText",
    "RehearsalMark",
    "InstrumentChange",
    "ScoreMetadata",
    # Parsing & Conversion
    "parse_score",
    "parse_mscx",
    "canonical_json",
    "canonical_hash",
    "score_to_mscx",
    "extract_mscx",
    "write_mscz",
    # Serialization
    "save_canonical",
    "load_score_from_json",
    # Merging
    "three_way_merge_scores",
    "MergeConflict",
    # Utilities
    "midi_to_pitch",
    "pitch_to_midi",
]

