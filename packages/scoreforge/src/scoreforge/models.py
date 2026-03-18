from dataclasses import dataclass
from typing import List, Union, Optional


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
class Rest:
    duration: float  # Base duration (without dots)
    dots: int = 0  # Number of augmentation dots (0, 1, or 2)


@dataclass(frozen=True)
class Dynamic:
    subtype: str  # e.g., "p", "f", "mf", etc.


Event = Union[Note, Rest, Dynamic]


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
    events: List[Event]
    key_sig: Optional[KeySig] = None
    time_sig: Optional[TimeSig] = None
    irregular: Optional[float] = None  # MuseScore irregular flag (0 or 1)
    measure_len: Optional[str] = None  # Actual length when different from time sig (e.g. "1/4" for pickup)


@dataclass
class Part:
    part_id: str
    measures: List[Measure]


@dataclass
class Score:
    parts: List[Part]
    score_id: Optional[str] = None
