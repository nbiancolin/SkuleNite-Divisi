"""XML parsing for MSCX files and canonical score hashing."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Optional

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


def _to_canonical_dict(obj) -> object:
    """Recursively convert a frozen dataclass tree to JSON-serialisable dicts."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, Fraction):
        return [obj.numerator, obj.denominator]
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, tuple):
        return [_to_canonical_dict(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        cls_name = type(obj).__name__
        d: dict = {"__type__": cls_name}
        for f_name in sorted(obj.__dataclass_fields__):
            d[f_name] = _to_canonical_dict(getattr(obj, f_name))
        return d
    return repr(obj)


def canonical_json(obj) -> str:
    """Return a canonical, sorted-key JSON string for any dataclass tree."""
    return json.dumps(_to_canonical_dict(obj), sort_keys=True, ensure_ascii=False)


def canonical_hash(obj) -> str:
    """Return a SHA-256 hex digest of the canonical JSON representation."""
    data = canonical_json(obj).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


_BARLINE_MAP = {
    "double": BarLineType.DOUBLE,
    "start-repeat": BarLineType.START_REPEAT,
    "end-repeat": BarLineType.END_REPEAT,
    "end-start-repeat": BarLineType.END_START_REPEAT,
    "final": BarLineType.FINAL,
    "dashed": BarLineType.DASHED,
    "dotted": BarLineType.DOTTED,
    "short": BarLineType.SHORT,
    "tick": BarLineType.TICK,
}

_HEAD_MAP = {
    "normal": NoteHeadType.NORMAL,
    "cross": NoteHeadType.CROSS,
    "diamond": NoteHeadType.DIAMOND,
    "slash": NoteHeadType.SLASH,
    "circle-x": NoteHeadType.CIRCLE_X,
    "circleX": NoteHeadType.CIRCLE_X,
    "do": NoteHeadType.DO,
    "re": NoteHeadType.RE,
    "mi": NoteHeadType.MI,
    "fa": NoteHeadType.FA,
    "sol": NoteHeadType.SOL,
    "la": NoteHeadType.LA,
    "si": NoteHeadType.SI,
    "triangle": NoteHeadType.TRIANGLE,
    "square": NoteHeadType.SQUARE,
}


def _txt(el: ET.Element, tag: str, default=None):
    child = el.find(tag)
    return child.text if child is not None else default


def _int(el: ET.Element, tag: str, default: int = 0) -> int:
    v = _txt(el, tag)
    return int(v) if v is not None else default


def _parse_note(note_el: ET.Element) -> Note:
    pitch = _int(note_el, "pitch")
    tpc = _int(note_el, "tpc")
    head_str = _txt(note_el, "head", "normal")
    head = _HEAD_MAP.get(head_str, NoteHeadType.NORMAL)

    has_start = False
    has_end = False
    for spanner in note_el.findall("Spanner"):
        if spanner.get("type") == "Tie":
            if spanner.find("next") is not None:
                has_start = True
            if spanner.find("prev") is not None:
                has_end = True

    symbols = {s.findtext("n", "") for s in note_el.findall("Symbol")}
    parenthesised = (
        "noteheadParenthesisLeft" in symbols
        or "noteheadParenthesisRight" in symbols
    )

    return Note(
        pitch=pitch,
        tpc=tpc,
        head=head,
        tie=TieInfo(has_tie_start=has_start, has_tie_end=has_end),
        parenthesised=parenthesised,
    )


def _parse_duration(el: ET.Element, current_time_sig: Optional[TimeSig] = None) -> Duration:
    dur_type = _txt(el, "durationType", "quarter")
    dots = _int(el, "dots", 0)

    ts_val = current_time_sig.measure_duration if current_time_sig else None
    if dur_type == "measure" and ts_val is None:
        dur_text = _txt(el, "duration")
        if dur_text and "/" in dur_text:
            n, d = dur_text.split("/")
            ts_val = Fraction(int(n), int(d))

    return Duration.from_mscx(dur_type, dots, ts_val)


def _parse_chord(chord_el: ET.Element, current_time_sig: Optional[TimeSig]) -> Chord:
    notes = tuple(sorted((_parse_note(n) for n in chord_el.findall("Note")), key=lambda n: n.pitch))
    duration = _parse_duration(chord_el, current_time_sig)
    arts = tuple(sorted(a.findtext("subtype", "") for a in chord_el.findall("Articulation")))
    no_stem = _txt(chord_el, "noStem") == "1"
    grace = None
    return Chord(
        notes=notes,
        duration=duration,
        articulations=arts,
        no_stem=no_stem,
        grace=grace,
    )


def _parse_rest(rest_el: ET.Element, current_time_sig: Optional[TimeSig]) -> Rest:
    return Rest(duration=_parse_duration(rest_el, current_time_sig))


def _parse_measure_repeat(mr_el: ET.Element, current_time_sig: Optional[TimeSig]) -> MeasureRepeat:
    count = _int(mr_el, "subtype", 1)
    duration = _parse_duration(mr_el, current_time_sig)
    return MeasureRepeat(count=count, duration=duration)


def _parse_spanner_event(sp_el: ET.Element) -> SpannerEvent | None:
    kind_str = sp_el.get("type", "")
    try:
        kind = SpannerKind(kind_str)
    except ValueError:
        return None

    is_start = sp_el.find("next") is not None
    inner = sp_el.find(kind_str)
    subtype = None
    if inner is not None:
        subtype = _txt(inner, "subtype")
    return SpannerEvent(kind=kind, is_start=is_start, subtype=subtype)


def _parse_voice(
    voice_el: ET.Element,
    voice_index: int,
    current_time_sig: Optional[TimeSig],
) -> Voice:
    events: list[VoiceEvent] = []
    for child in voice_el:
        tag = child.tag
        if tag == "Chord":
            events.append(_parse_chord(child, current_time_sig))
        elif tag == "Rest":
            events.append(_parse_rest(child, current_time_sig))
        elif tag == "MeasureRepeat":
            events.append(_parse_measure_repeat(child, current_time_sig))
        elif tag == "Spanner":
            ev = _parse_spanner_event(child)
            if ev is not None:
                events.append(ev)
    return Voice(voice_index=voice_index, events=tuple(events))


def _parse_annotations(measure_el: ET.Element) -> list[Annotation]:
    anns: list[Annotation] = []
    candidates = list(measure_el)
    for voice_el in measure_el.findall("voice"):
        candidates.extend(voice_el)

    for child in candidates:
        tag = child.tag
        if tag == "Dynamic":
            subtype = _txt(child, "subtype", "")
            vel_str = _txt(child, "velocity")
            vel = int(vel_str) if vel_str else None
            anns.append(Dynamic(subtype=subtype, velocity=vel))
        elif tag == "StaffText":
            txt = _txt(child, "text", "")
            if txt:
                anns.append(StaffText(text=txt))
        elif tag == "RehearsalMark":
            txt = _txt(child, "text", "")
            if txt:
                anns.append(RehearsalMark(text=txt))
        elif tag == "InstrumentChange":
            inst_el = child.find("Instrument")
            inst_id = inst_el.get("id", "") if inst_el is not None else ""
            label = _txt(child, "text")
            anns.append(InstrumentChange(instrument_id=inst_id, label=label))
    return anns


def _parse_measure(
    measure_el: ET.Element,
    measure_number: int,
    current_key: Optional[KeySig],
    current_time: Optional[TimeSig],
) -> tuple[Measure, Optional[KeySig], Optional[TimeSig]]:
    new_key = None
    new_time = None
    tempo = None
    bar_line = None
    is_irregular = measure_el.find("irregular") is not None

    for voice_el in measure_el.findall("voice"):
        for child in voice_el:
            tag = child.tag
            if tag == "KeySig":
                fifths = _int(child, "concertKey", 0)
                mode = _txt(child, "mode")
                new_key = KeySig(fifths=fifths, mode=mode)
            elif tag == "TimeSig":
                sig_n = _int(child, "sigN", 4)
                sig_d = _int(child, "sigD", 4)
                new_time = TimeSig(numerator=sig_n, denominator=sig_d)
            elif tag == "Tempo":
                bpm_text = _txt(child, "tempo")
                bpm = float(bpm_text) * 60 if bpm_text else 120.0
                tempo_text = _txt(child, "text")
                tempo = Tempo(bpm=bpm, text=tempo_text)
        break

    for voice_el in measure_el.findall("voice"):
        bl_el = voice_el.find("BarLine")
        if bl_el is not None:
            subtype = _txt(bl_el, "subtype", "normal")
            bar_line = _BARLINE_MAP.get(subtype)

    effective_time = new_time if new_time is not None else current_time
    voices_list: list[Voice] = []
    for i, voice_el in enumerate(measure_el.findall("voice")):
        v = _parse_voice(voice_el, i, effective_time)
        if v.events:
            voices_list.append(v)

    annotations = tuple(_parse_annotations(measure_el))
    measure = Measure(
        number=measure_number,
        voices=tuple(voices_list),
        key_sig=new_key,
        time_sig=new_time,
        tempo=tempo,
        bar_line=bar_line,
        annotations=annotations,
        is_irregular=is_irregular,
    )
    return measure, new_key or current_key, new_time or current_time


def _parse_staff(staff_el: ET.Element, staff_id: int, clef: Optional[str], is_drum: bool) -> Staff:
    measures: list[Measure] = []
    measure_number = 1
    current_key: Optional[KeySig] = None
    current_time: Optional[TimeSig] = None
    # MuseScore's XML nesting varies a bit across MSCX exports.
    # Try direct measures first; if none are found, fall back to descendant search.
    measure_els = staff_el.findall("Measure")
    if not measure_els:
        measure_els = staff_el.findall(".//Measure")

    for m_el in measure_els:
        m, current_key, current_time = _parse_measure(
            m_el,
            measure_number,
            current_key,
            current_time,
        )
        measures.append(m)
        measure_number += 1
    return Staff(staff_id=staff_id, measures=tuple(measures), clef=clef, is_drum=is_drum)


def _parse_score_element(score_el: ET.Element) -> Score:
    def meta(name: str) -> Optional[str]:
        for el in score_el.findall("metaTag"):
            if el.get("name") == name:
                return el.text or None
        return None

    metadata = ScoreMetadata(
        title=meta("workTitle") or "",
        subtitle=meta("subtitle"),
        composer=meta("composer"),
        lyricist=meta("lyricist"),
        arranger=meta("arranger"),
        copyright=meta("copyright"),
    )
    division = int(score_el.findtext("Division", "480"))

    staff_meta: dict[int, dict] = {}
    for part_el in score_el.findall("Part"):
        part_id = part_el.get("id", "")
        inst_el = part_el.find("Instrument")
        inst_id = inst_el.get("id", "") if inst_el is not None else ""
        name = _txt(part_el, "trackName") or ""
        is_drum = inst_el is not None and inst_el.findtext("useDrumset") == "1"
        default_clef = _txt(inst_el, "clef") if inst_el is not None else None
        for staff_el in part_el.findall("Staff"):
            sid = int(staff_el.get("id", "0"))
            clef = staff_el.findtext("defaultClef") or default_clef
            staff_meta[sid] = dict(
                part_id=part_id,
                instrument_id=inst_id,
                name=name,
                clef=clef,
                is_drum=is_drum,
            )

    parsed_staves: dict[int, Staff] = {}
    for staff_el in score_el.findall("Staff"):
        sid = int(staff_el.get("id", "0"))
        sm = staff_meta.get(sid, {})
        parsed_staves[sid] = _parse_staff(
            staff_el,
            staff_id=sid,
            clef=sm.get("clef"),
            is_drum=sm.get("is_drum", False),
        )

    # MuseScore MSCX exports often omit numeric staff `id` from <Part><Staff> references.
    # Instead of using unstable ids/eids, map by deterministic consumption order:
    # - Take all <Score><Staff> definitions in document order.
    # - For each <Score><Part>, consume as many staff definitions as it has <Part><Staff> children.
    staff_def_ids_in_order: list[int] = [
        int(s_el.get("id", "0"))
        for s_el in score_el.findall("Staff")
        if s_el.get("id") is not None
    ]
    staff_def_cursor = 0

    parts: list[Part] = []
    for part_el in score_el.findall("Part"):
        part_id = part_el.get("id", "")
        inst_el = part_el.find("Instrument")
        inst_id = inst_el.get("id", "") if inst_el is not None else ""
        name = _txt(part_el, "trackName") or ""

        part_staff_ref_count = len(part_el.findall("Staff"))
        staves: list[Staff] = []
        for _ in range(part_staff_ref_count):
            if staff_def_cursor >= len(staff_def_ids_in_order):
                break
            sid = staff_def_ids_in_order[staff_def_cursor]
            staff_def_cursor += 1
            if sid in parsed_staves:
                staves.append(parsed_staves[sid])

        parts.append(Part(part_id=part_id, instrument_id=inst_id, name=name, staves=tuple(staves)))
    return Score(metadata=metadata, parts=tuple(parts), division=division)


def parse_mscx(path: str | Path) -> Score:
    """Parse a MuseScore MSCX file and return a canonical Score object."""
    tree = ET.parse(path)
    root = tree.getroot()
    score_el = root.find("Score")
    if score_el is None:
        raise ValueError("No <Score> element found in MSCX file.")
    return _parse_score_element(score_el)


def parse_score(tree: ET.ElementTree) -> Score:
    """Parse an MSCX ElementTree into a canonical Score object."""
    root = tree.getroot()
    score_el = root.find("Score")
    if score_el is None:
        raise ValueError("No <Score> element found in MSCX tree.")
    return _parse_score_element(score_el)
