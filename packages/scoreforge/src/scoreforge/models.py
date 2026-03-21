from dataclasses import dataclass, field
from typing import List, Union, Optional, Dict


@dataclass(frozen=True)
class SlurStart:
    """Represents the start of a slur."""
    next_fractions: str  # Fractions offset to the end (e.g., "7/8")


@dataclass(frozen=True)
class SlurEnd:
    """Represents the end of a slur."""
    prev_fractions: str  # Fractions offset from the start (e.g., "-7/8")


@dataclass(frozen=True)
class TieStart:
    """Represents the start of a tie."""
    next_fractions: str  # Fractions offset to the end (e.g., "1/8" or "1" for measures)


@dataclass(frozen=True)
class TieEnd:
    """Represents the end of a tie."""
    prev_fractions: str  # Fractions offset from the start (e.g., "-1/8" or "-1" for measures)


@dataclass(frozen=True)
class Note:
    pitch: str
    duration: float  # Base duration (without dots)
    dots: int = 0  # Number of augmentation dots (0, 1, or 2)
    slur_start: Optional[SlurStart] = None
    slur_end: Optional[SlurEnd] = None
    tie_start: Optional[TieStart] = None
    tie_end: Optional[TieEnd] = None


@dataclass(frozen=True)
class ChordNote:
    """One pitch inside a multi-note chord (ties only; slurs live on ChordGroup)."""

    pitch: str
    tie_start: Optional[TieStart] = None
    tie_end: Optional[TieEnd] = None


@dataclass(frozen=True)
class ChordGroup:
    """Simultaneous chord: one rhythmic unit, multiple stacked pitches (MuseScore one <Chord>)."""

    notes: tuple[ChordNote, ...]
    duration: float
    dots: int = 0
    slur_start: Optional[SlurStart] = None
    slur_end: Optional[SlurEnd] = None


@dataclass(frozen=True)
class Rest:
    duration: float  # Base duration (without dots); unused when measure_duration is set
    dots: int = 0  # Number of augmentation dots (0, 1, or 2)
    measure_duration: Optional[str] = None  # e.g. "4/4" for full-measure rests (durationType measure)


@dataclass(frozen=True)
class Dynamic:
    subtype: str  # e.g., "p", "f", "mf", etc.


@dataclass(frozen=True)
class HairpinStart:
    """Start of a hairpin (crescendo / diminuendo) — MuseScore <Spanner type=\"HairPin\"> with <next>."""

    subtype: str  # MuseScore hairpin kind (e.g. "1" cresc., "3" dim. — preserve for round-trip)
    next_measures: Optional[str] = None
    next_fractions: Optional[str] = None
    direction: Optional[str] = None  # e.g. "up", "down"


@dataclass(frozen=True)
class HairpinEnd:
    """End anchor for a hairpin — <Spanner type=\"HairPin\"> with <prev> only."""

    prev_measures: Optional[str] = None
    prev_fractions: Optional[str] = None


@dataclass(frozen=True)
class MeasureRepeat:
    """One-measure repeat sign (percent) as in MuseScore <MeasureRepeat>."""

    subtype: str  # e.g. "1" for single-slash staff repeat
    duration_type: str  # typically "measure"
    duration: str  # e.g. "4/4" — span relative to time signature


Event = Union[
    Note,
    ChordGroup,
    Rest,
    Dynamic,
    HairpinStart,
    HairpinEnd,
    MeasureRepeat,
]


@dataclass(frozen=True)
class KeySig:
    concert_key: int


@dataclass(frozen=True)
class TimeSig:
    sig_n: int  # numerator
    sig_d: int  # denominator


@dataclass
class Measure:
    number: int
    voices: Dict[str, List[Event]] = field(default_factory=dict)
    key_sig: Optional[KeySig] = None
    time_sig: Optional[TimeSig] = None
    irregular: Optional[float] = None  # MuseScore irregular flag (0 or 1)
    measure_len: Optional[str] = None  # Actual length when different from time sig (e.g. "1/4" for pickup)
    measure_repeat_count: Optional[int] = None  # MuseScore <measureRepeatCount> on Measure (e.g. 1)
    double_bar: bool = False  # End-of-measure double barline (<BarLine><subtype>double</subtype>)

    @property
    def events(self) -> List[Event]:
        """Voice 0 only; kept for backward compatibility with single-voice scores."""
        return self.voices.get("0", [])


@dataclass
class Part:
    part_id: str
    measures: List[Measure]


@dataclass
class Score:
    parts: List[Part]
    score_id: Optional[str] = None
