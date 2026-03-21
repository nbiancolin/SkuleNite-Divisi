from __future__ import annotations
 
from dataclasses import dataclass, field
from fractions import Fraction
from enum import Enum
from typing import Optional

"""
Hierarchy
---------
  Score
  └── parts: tuple[Part]
      └── staves: tuple[Staff]
          └── measures: tuple[Measure]
              ├── key_sig:   KeySig | None
              ├── time_sig:  TimeSig | None
              ├── tempo:     Tempo | None
              ├── bar_line:  BarLineType | None   (non-standard ending barline)
              ├── repeat:    RepeatMarker | None
              ├── voices:    tuple[Voice]          (indexed 0-based)
              │   └── events: tuple[VoiceEvent]
              │       ├── Chord
              │       │   ├── notes:         tuple[Note]
              │       │   ├── articulations: tuple[str]
              │       │   └── duration:      Duration
              │       ├── Rest
              │       ├── MeasureRepeat
              │       └── SpannerEvent  (ottava, slur, hairpin …)
              └── annotations: tuple[Annotation]
                  ├── Dynamic
                  ├── StaffText
                  ├── InstrumentChange
                  └── RehearsalMark
"""

# ---------------------------------------------------------------------------
# Primitive types
# ---------------------------------------------------------------------------
 
class BarLineType(str, Enum):
    """Barline subtypes that affect musical reading (normal is implicit)."""
    NORMAL        = "normal"
    DOUBLE        = "double"
    START_REPEAT  = "start-repeat"
    END_REPEAT    = "end-repeat"
    END_START_REPEAT = "end-start-repeat"
    FINAL         = "final"
    DASHED        = "dashed"
    DOTTED        = "dotted"
    SHORT         = "short"
    TICK          = "tick"
 
 
class NoteHeadType(str, Enum):
    """Noteheads that carry musical meaning."""
    NORMAL       = "normal"
    CROSS        = "cross"
    DIAMOND      = "diamond"
    SLASH        = "slash"
    CIRCLE_X     = "circle-x"
    TRIANGLE     = "triangle"
    SQUARE       = "square"
    DO           = "do"
    RE           = "re"
    MI           = "mi"
    FA           = "fa"
    SOL          = "sol"
    LA           = "la"
    SI           = "si"
    PARENTHESISED = "parenthesised"
 
 
# ---------------------------------------------------------------------------
# Duration
# ---------------------------------------------------------------------------
 
_DURATION_TYPE_TO_FRACTION: dict[str, Fraction] = {
    "long":     Fraction(4, 1),
    "breve":    Fraction(2, 1),
    "whole":    Fraction(1, 1),
    "half":     Fraction(1, 2),
    "quarter":  Fraction(1, 4),
    "eighth":   Fraction(1, 8),
    "16th":     Fraction(1, 16),
    "32nd":     Fraction(1, 32),
    "64th":     Fraction(1, 64),
    "128th":    Fraction(1, 128),
    "256th":    Fraction(1, 256),
    "measure":  Fraction(0),   # placeholder; actual value from <duration>
}
 
 
@dataclass(frozen=True, order=True)
class Duration:
    """
    A rhythmic duration expressed as a rational fraction of a whole note.
 
    Examples
    --------
    quarter          → Duration(Fraction(1, 4), dots=0)
    dotted quarter   → Duration(Fraction(3, 8), dots=1)
    double-dotted 8th→ Duration(Fraction(7, 32), dots=2)
    whole-measure    → Duration(Fraction(1, 1), dots=0, is_measure_rest=True)
    """
    value: Fraction          # actual duration in whole notes
    dots: int = 0
    is_measure_rest: bool = False   # True when <durationType>measure</durationType>
    tuplet_ratio: Optional[tuple[int, int]] = None  # (actual, normal), e.g. (3,2) for triplet
 
    @staticmethod
    def from_mscx(
        duration_type: str,
        dots: int = 0,
        time_sig_value: Optional[Fraction] = None,
        tuplet_ratio: Optional[tuple[int, int]] = None,
    ) -> "Duration":
        """
        Build a Duration from MSCX fields.
 
        Parameters
        ----------
        duration_type:
            The text of <durationType> (e.g. "quarter", "measure").
        dots:
            Number of augmentation dots (from <dots> child element count).
        time_sig_value:
            Required only when duration_type == "measure"; gives the measure's
            full duration so the value can be set correctly.
        tuplet_ratio:
            (actual, normal) ratio, e.g. (3, 2) for a triplet.
        """
        if duration_type == "measure":
            base = time_sig_value if time_sig_value is not None else Fraction(1)
            return Duration(value=base, dots=0, is_measure_rest=True,
                            tuplet_ratio=tuplet_ratio)
 
        base = _DURATION_TYPE_TO_FRACTION.get(duration_type, Fraction(1, 4))
        # Apply dots: d_dots = base * (2 - 1/2^dots)
        value = base
        dot_add = base
        for _ in range(dots):
            dot_add = dot_add / 2
            value += dot_add
 
        if tuplet_ratio:
            actual, normal = tuplet_ratio
            value = value * Fraction(normal, actual)
 
        return Duration(value=value, dots=dots, is_measure_rest=False,
                        tuplet_ratio=tuplet_ratio)
 
    def __str__(self) -> str:
        dot_str = "." * self.dots
        if self.is_measure_rest:
            return f"measure({self.value})"
        return f"{self.value}{dot_str}"
 
 
# ---------------------------------------------------------------------------
# Key / Time signatures
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class KeySig:
    """
    Concert-pitch key signature.
 
    fifths: number of sharps (positive) or flats (negative) in the key.
    mode:   'major' | 'minor' | 'dorian' | … (None if not specified).
    """
    fifths: int
    mode: Optional[str] = None
 
 
@dataclass(frozen=True)
class TimeSig:
    """
    Time signature as an exact fraction (beats / beat_unit).
 
    Examples
    --------
    4/4  → TimeSig(numerator=4, denominator=4)
    6/8  → TimeSig(numerator=6, denominator=8)
    5/4  → TimeSig(numerator=5, denominator=4)
    """
    numerator: int
    denominator: int
 
    @property
    def measure_duration(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)
 
 
# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Tempo:
    """
    Metronome tempo mark.
 
    bpm:           quarter-note beats per minute (float for precision).
    beat_duration: the beat unit as a Duration (defaults to quarter).
    text:          optional text label, e.g. "Moderato", "♩ = 120".
    """
    bpm: float
    beat_duration: Duration = field(
        default_factory=lambda: Duration(Fraction(1, 4))
    )
    text: Optional[str] = None
 
 
# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True, order=True)
class TieInfo:
    """
    Records that a note participates in a tie.
 
    has_tie_start: this note begins a tie (connects forward).
    has_tie_end:   this note ends a tie (connected from previous note).
 
    Both can be True for a note in the middle of a long tie chain.
    """
    has_tie_start: bool = False
    has_tie_end:   bool = False
 
 
@dataclass(frozen=True, order=True)
class Note:
    """
    A single pitch within a Chord.
 
    pitch:          MIDI pitch number (0-127).
    tpc:            Tonal Pitch Class (-1 … 33, canonical enharmonic spelling).
    head:           notehead type (NoteHeadType enum value).
    tie:            tie connectivity.
    parenthesised:  True when the note has noteheadParenthesisLeft/Right symbols.
    """
    pitch: int
    tpc: int
    head: NoteHeadType = NoteHeadType.NORMAL
    tie: TieInfo = field(default_factory=TieInfo)
    parenthesised: bool = False
 
    def midi_pitch(self) -> int:
        return self.pitch
 
    def octave(self) -> int:
        return self.pitch // 12 - 1
 
    def pitch_class(self) -> int:
        return self.pitch % 12
 
 
# ---------------------------------------------------------------------------
# Voice events
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Chord:
    """
    A rhythmic event that sounds one or more pitches simultaneously.
 
    notes:         sorted tuple of Note (by pitch ascending) for determinism.
    duration:      rhythmic duration.
    articulations: sorted tuple of articulation subtype strings.
    no_stem:       True for stemless noteheads (e.g. slash notation).
    grace:         grace-note kind ('acciaccatura' | 'appoggiatura' | None).
    """
    notes: tuple[Note, ...]
    duration: Duration
    articulations: tuple[str, ...] = ()
    no_stem: bool = False
    grace: Optional[str] = None
 
 
@dataclass(frozen=True)
class Rest:
    """A rest of a given duration."""
    duration: Duration
 
 
@dataclass(frozen=True)
class MeasureRepeat:
    """
    A measure-repeat symbol.
 
    count: how many preceding measures are repeated (1 or 2).
    """
    count: int
    duration: Duration   # full-measure duration for beat-accounting purposes
 
 
class SpannerKind(str, Enum):
    TIE          = "Tie"         # note-level; also captured on Note.tie
    SLUR         = "Slur"
    HAIRPIN      = "Hairpin"     # crescendo / decrescendo
    OTTAVA       = "Ottava"      # 8va, 8vb, 15ma, …
    PEDAL        = "Pedal"
    TRILL        = "Trill"
    VOLTA        = "Volta"       # 1st/2nd ending bracket
    GLISSANDO    = "Glissando"
    VIBRATO      = "Vibrato"
    TEMPO_CHANGE = "GradualTempoChange"
 
 
@dataclass(frozen=True)
class SpannerEvent:
    """
    The start or end anchor of a cross-element spanner (slur, hairpin, etc.).
 
    kind:      SpannerKind enum.
    is_start:  True = this event marks where the spanner begins.
    subtype:   spanner-specific subtype, e.g. "8va", "cresc.", "1." (volta).
    """
    kind: SpannerKind
    is_start: bool
    subtype: Optional[str] = None
 
 
# Union of all events that can appear inside a voice stream.
VoiceEvent = Chord | Rest | MeasureRepeat | SpannerEvent
 
 
# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Voice:
    """
    A single rhythmic voice within a measure (voice 0-3 in MSCX).
 
    voice_index: 0-based (MSCX uses 0-indexed internally).
    events:      ordered tuple of VoiceEvent as they appear in time.
    """
    voice_index: int
    events: tuple[VoiceEvent, ...]
 
 
# ---------------------------------------------------------------------------
# Annotations (measure-level, not voice-specific)
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Dynamic:
    """
    A dynamic marking (pp, mp, f, fff, sfz, …).
 
    subtype:  the marking name as a string (matches MSCX <subtype>).
    velocity: MIDI velocity if explicitly set, else None.
    """
    subtype: str
    velocity: Optional[int] = None
 
 
@dataclass(frozen=True)
class StaffText:
    """Free-text annotation attached to the staff at this measure."""
    text: str
 
 
@dataclass(frozen=True)
class RehearsalMark:
    """Rehearsal letter / number / label."""
    text: str
 
 
@dataclass(frozen=True)
class InstrumentChange:
    """
    Mid-score instrument change.
 
    instrument_id: the MuseScore instrument identifier string, e.g. "electric-guitar".
    label:         optional printed text (e.g. "To Shaker").
    """
    instrument_id: str
    label: Optional[str] = None
 
 
# Union type for annotations
Annotation = Dynamic | StaffText | RehearsalMark | InstrumentChange
 
 
# ---------------------------------------------------------------------------
# Measure
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Measure:
    """
    A single measure for one staff.
 
    Fields
    ------
    number:
        1-based measure number within the staff (pickup bar = 1 if it exists,
        or 0 if you prefer to distinguish it).
    key_sig:
        Present only when the key signature *changes* at this measure.
    time_sig:
        Present only when the time signature *changes* at this measure.
    tempo:
        Present only when a tempo marking begins at this measure.
    bar_line:
        Non-standard barline *at the end* of this measure.  A normal
        single barline is None (implicit).
    voices:
        Tuple of Voice objects in voice-index order. Empty voices are omitted.
    annotations:
        Measure-level annotations (dynamics, text, instrument changes, etc.)
        in document order.
    is_irregular:
        True for pickup bars or explicitly shortened measures (<irregular> tag).
    """
    number: int
    voices: tuple[Voice, ...]
    key_sig: Optional[KeySig] = None
    time_sig: Optional[TimeSig] = None
    tempo: Optional[Tempo] = None
    bar_line: Optional[BarLineType] = None
    annotations: tuple[Annotation, ...] = ()
    is_irregular: bool = False
 
 
# ---------------------------------------------------------------------------
# Staff / Part / Score
# ---------------------------------------------------------------------------
 
@dataclass(frozen=True)
class Staff:
    """
    One staff (stave) within a part.
 
    staff_id:   1-based staff number as declared in the MSCX <Staff id="…">.
    measures:   tuple of Measure in score order.
    clef:       initial clef token (e.g. "G", "F", "PERC", "G8vb").
    is_drum:    True when the staff uses a drum notation map.
    """
    staff_id: int
    measures: tuple[Measure, ...]
    clef: Optional[str] = None
    is_drum: bool = False
 
 
@dataclass(frozen=True)
class Part:
    """
    A musical part (instrument).
 
    part_id:       MSCX part id string.
    instrument_id: e.g. "electric-guitar", "piano", "drum-kit-5".
    name:          Long name of the instrument.
    staves:        tuple of Staff belonging to this part.
    """
    part_id: str
    instrument_id: str
    name: str
    staves: tuple[Staff, ...]
 
 
@dataclass(frozen=True)
class ScoreMetadata:
    """
    Stable score-level metadata.
 
    Only fields with musical / identification relevance are kept; editor
    preferences, revision IDs, and platform info are excluded.
    """
    title: str
    subtitle: Optional[str] = None
    composer: Optional[str] = None
    lyricist: Optional[str] = None
    arranger: Optional[str] = None
    copyright: Optional[str] = None
 
 
@dataclass(frozen=True)
class Score:
    """
    Top-level canonical representation of a score.
 
    metadata: title, composer, etc.
    parts:    ordered tuple of Part as they appear in the score.
    division: MSCX ticks-per-quarter-note (for reference only; not used in
              canonical durations which are fractional).
    """
    metadata: ScoreMetadata
    parts: tuple[Part, ...]
    division: int = 480