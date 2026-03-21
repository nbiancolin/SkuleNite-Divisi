"""XML parsing for MSCX files."""

import xml.etree.ElementTree as ET

from scoreforge.models import (
    Score,
    Note,
    Measure,
    Part,
    Rest,
    Event,
    KeySig,
    TimeSig,
    Dynamic,
    SlurStart,
    SlurEnd,
    TieStart,
    TieEnd,
    MeasureRepeat,
    ChordGroup,
    ChordNote,
    HairpinStart,
    HairpinEnd,
    OttavaStart,
    OttavaEnd,
    StaffText,
    RehearsalMark,
    InstrumentChange,
    LayoutBreak,
    VBoxFrame,
    FrameText,
)
from scoreforge.converter import midi_to_pitch
from scoreforge.mscx_util import element_to_json


# Duration mapping from MSCX format to numeric values (base length, dots separate)
def _opt_text(txt: str | None) -> str | None:
    if txt is None:
        return None
    s = str(txt).strip()
    return s if s else None


def _opt_int(txt: str | None) -> int | None:
    if txt is None or not str(txt).strip():
        return None
    try:
        return int(str(txt).strip())
    except ValueError:
        return None


def _opt_bool01(txt: str | None) -> bool | None:
    if txt is None or not str(txt).strip():
        return None
    s = str(txt).strip()
    if s == "1":
        return True
    if s == "0":
        return False
    return None


DURATION_MAP = {
    "whole": 4,
    "half": 2,
    "quarter": 1,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
    "64th": 0.0625,
}


def _measure_has_double_barline(measure_el: ET.Element) -> bool:
    """True if this measure has a MuseScore double barline (MS4 often nests <BarLine> under <voice>)."""
    for bar in measure_el.findall(".//BarLine"):
        if (bar.findtext("subtype") or "").strip() == "double":
            return True
    return False


def _parse_measure_repeat_count(measure_el: ET.Element) -> int | None:
    t = measure_el.findtext("measureRepeatCount")
    if t is None or not str(t).strip():
        return None
    try:
        return int(t.strip())
    except ValueError:
        return None


def _parse_single_voice_content(
    voice_el: ET.Element,
    active_slur_starts: list,
    active_tie_starts: list,
) -> tuple[list[Event], KeySig | None, TimeSig | None]:
    """Parse one <voice> container: events plus any KeySig/TimeSig inside it."""
    events: list[Event] = []
    key_sig = None
    time_sig = None

    for el in list(voice_el):
            # ---- KEYSIG ----
            if el.tag == "KeySig":
                cand = KeySig(
                    concert_key=_opt_int(el.findtext("concertKey")),
                    custom=_opt_int(el.findtext("custom")),
                    mode=_opt_text(el.findtext("mode")),
                )
                if (
                    cand.concert_key is not None
                    or cand.custom is not None
                    or cand.mode is not None
                ):
                    key_sig = cand
                continue
            
            # ---- TIMESIG ----
            elif el.tag == "TimeSig":
                sig_n_text = el.findtext("sigN")
                sig_d_text = el.findtext("sigD")
                if sig_n_text is not None and sig_d_text is not None:
                    time_sig = TimeSig(
                        sig_n=int(sig_n_text),
                        sig_d=int(sig_d_text),
                    )
                continue

            # ---- CHORD ----
            elif el.tag == "Chord":
                dur_type = el.findtext("durationType", "quarter")
                base_duration = DURATION_MAP.get(dur_type, 1)

                dots_text = el.findtext("dots", "0")
                try:
                    dots = int(dots_text)
                except ValueError:
                    dots = 0
                dots = max(0, min(2, dots))

                stem_direction = _opt_text(el.findtext("StemDirection"))
                no_stem = (el.findtext("noStem") or "").strip() == "1"
                articulations = tuple(
                    st
                    for a in el.findall("Articulation")
                    for st in [(_opt_text(a.findtext("subtype")) or "")]
                    if st
                )

                slur_start = None
                slur_end = None
                for spanner_el in el.findall("Spanner"):
                    if spanner_el.get("type") == "Slur":
                        next_el = spanner_el.find("next")
                        if next_el is not None:
                            location_el = next_el.find("location")
                            if location_el is not None:
                                fractions = location_el.findtext("fractions")
                                if fractions:
                                    slur_start = SlurStart(next_fractions=fractions)
                                    active_slur_starts.append(fractions)

                        prev_el = spanner_el.find("prev")
                        if prev_el is not None:
                            location_el = prev_el.find("location")
                            if location_el is not None:
                                fractions = location_el.findtext("fractions")
                                if fractions:
                                    if active_slur_starts:
                                        active_slur_starts.pop()
                                    slur_end = SlurEnd(prev_fractions=fractions)

                chord_notes: list[ChordNote] = []
                for note_el in el.findall("Note"):
                    pitch_txt = note_el.findtext("pitch")
                    pitch = int(pitch_txt) if pitch_txt is not None and str(pitch_txt).strip() else 0

                    tie_start = None
                    tie_end = None
                    for spanner_el in note_el.findall("Spanner"):
                        if spanner_el.get("type") == "Tie":
                            next_el = spanner_el.find("next")
                            if next_el is not None:
                                location_el = next_el.find("location")
                                if location_el is not None:
                                    fractions = location_el.findtext("fractions")
                                    measures_offset = location_el.findtext("measures")
                                    offset = fractions if fractions else measures_offset
                                    if offset:
                                        tie_start = TieStart(next_fractions=offset)
                                        active_tie_starts.append(offset)

                            prev_el = spanner_el.find("prev")
                            if prev_el is not None:
                                location_el = prev_el.find("location")
                                if location_el is not None:
                                    fractions = location_el.findtext("fractions")
                                    measures_offset = location_el.findtext("measures")
                                    offset = fractions if fractions else measures_offset
                                    if offset:
                                        if active_tie_starts:
                                            active_tie_starts.pop()
                                        tie_end = TieEnd(prev_fractions=offset)

                    sym_names = tuple(
                        nm
                        for sym in note_el.findall("Symbol")
                        for nm in [(_opt_text(sym.findtext("name")) or "")]
                        if nm
                    )

                    chord_notes.append(
                        ChordNote(
                            pitch=midi_to_pitch(pitch),
                            tie_start=tie_start,
                            tie_end=tie_end,
                            tpc=_opt_int(note_el.findtext("tpc")),
                            symbols=sym_names,
                            head=_opt_text(note_el.findtext("head")),
                            play=_opt_bool01(note_el.findtext("play")),
                            fixed=_opt_bool01(note_el.findtext("fixed")),
                            fixed_line=_opt_int(note_el.findtext("fixedLine")),
                        )
                    )

                if len(chord_notes) == 1:
                    cn = chord_notes[0]
                    events.append(
                        Note(
                            pitch=cn.pitch,
                            duration=base_duration,
                            dots=dots,
                            slur_start=slur_start,
                            slur_end=slur_end,
                            tie_start=cn.tie_start,
                            tie_end=cn.tie_end,
                            stem_direction=stem_direction,
                            no_stem=no_stem,
                            articulations=articulations,
                            tpc=cn.tpc,
                            symbols=cn.symbols,
                            head=cn.head,
                            play=cn.play,
                            fixed=cn.fixed,
                            fixed_line=cn.fixed_line,
                        )
                    )
                else:
                    events.append(
                        ChordGroup(
                            notes=tuple(chord_notes),
                            duration=base_duration,
                            dots=dots,
                            slur_start=slur_start,
                            slur_end=slur_end,
                            stem_direction=stem_direction,
                            no_stem=no_stem,
                            articulations=articulations,
                        )
                    )

            # ---- REST ----
            elif el.tag == "Rest":
                dur_type = el.findtext("durationType", "quarter")
                if dur_type == "measure":
                    md = el.findtext("duration")
                    if md is None or not str(md).strip():
                        md = "4/4"
                    else:
                        md = str(md).strip()
                    events.append(
                        Rest(
                            duration=0.0,
                            dots=0,
                            measure_duration=md,
                        )
                    )
                    continue

                base_duration = DURATION_MAP.get(dur_type, 1)

                # Parse dots
                dots_text = el.findtext("dots", "0")
                try:
                    dots = int(dots_text)
                except ValueError:
                    dots = 0
                # Clamp dots to valid range (0-2)
                dots = max(0, min(2, dots))

                events.append(
                    Rest(
                        duration=base_duration,  # Store base duration
                        dots=dots,  # Store dots separately
                    )
                )
            
            # ---- DYNAMIC ----
            elif el.tag == "Dynamic":
                subtype = el.findtext("subtype", "")
                if subtype:
                    events.append(
                        Dynamic(
                            subtype=subtype,
                            velocity=_opt_int(el.findtext("velocity")),
                        )
                    )
                continue

            # ---- HAIRPIN (crescendo / diminuendo) ----
            elif el.tag == "Spanner" and el.get("type") == "HairPin":
                next_el = el.find("next")
                prev_el = el.find("prev")
                if next_el is not None:
                    loc = next_el.find("location")
                    nm = _opt_text(loc.findtext("measures")) if loc is not None else None
                    nf = _opt_text(loc.findtext("fractions")) if loc is not None else None
                    hp_inner = el.find("HairPin")
                    subtype = "0"
                    direction = None
                    if hp_inner is not None:
                        subtype = _opt_text(hp_inner.findtext("subtype")) or "0"
                        direction = _opt_text(hp_inner.findtext("direction"))
                    events.append(
                        HairpinStart(
                            subtype=subtype,
                            next_measures=nm,
                            next_fractions=nf,
                            direction=direction,
                        )
                    )
                elif prev_el is not None:
                    loc = prev_el.find("location")
                    pm = _opt_text(loc.findtext("measures")) if loc is not None else None
                    pf = _opt_text(loc.findtext("fractions")) if loc is not None else None
                    events.append(
                        HairpinEnd(prev_measures=pm, prev_fractions=pf)
                    )
                continue

            # ---- OTTAVA ----
            elif el.tag == "Spanner" and el.get("type") == "Ottava":
                next_el = el.find("next")
                prev_el = el.find("prev")
                if next_el is not None:
                    loc = next_el.find("location")
                    nm = _opt_text(loc.findtext("measures")) if loc is not None else None
                    nf = _opt_text(loc.findtext("fractions")) if loc is not None else None
                    ot = el.find("Ottava")
                    subtype = _opt_text(ot.findtext("subtype")) if ot is not None else None
                    if not subtype:
                        subtype = "8va"
                    events.append(
                        OttavaStart(
                            subtype=subtype,
                            next_measures=nm,
                            next_fractions=nf,
                        )
                    )
                elif prev_el is not None:
                    loc = prev_el.find("location")
                    pm = _opt_text(loc.findtext("measures")) if loc is not None else None
                    pf = _opt_text(loc.findtext("fractions")) if loc is not None else None
                    events.append(OttavaEnd(prev_measures=pm, prev_fractions=pf))
                continue

            # ---- STAFF TEXT ----
            elif el.tag == "StaffText":
                txt = el.findtext("text")
                events.append(StaffText(text=(txt or "").strip()))
                continue

            # ---- REHEARSAL MARK ----
            elif el.tag == "RehearsalMark":
                txt = el.findtext("text")
                events.append(RehearsalMark(text=(txt or "").strip()))
                continue

            # ---- INSTRUMENT CHANGE ----
            elif el.tag == "InstrumentChange":
                inst_el = el.find("Instrument")
                inst_tree = element_to_json(inst_el) if inst_el is not None else {"tag": "Instrument"}
                events.append(
                    InstrumentChange(
                        text=(el.findtext("text") or "").strip(),
                        init=_opt_text(el.findtext("init")),
                        instrument_tree=inst_tree,
                    )
                )
                continue

            # ---- MEASURE REPEAT (percent sign) ----
            elif el.tag == "MeasureRepeat":
                subtype = el.findtext("subtype", "1") or "1"
                dur_type = el.findtext("durationType", "measure") or "measure"
                dur_frac = el.findtext("duration", "4/4")
                if dur_frac is None or not str(dur_frac).strip():
                    dur_frac = "4/4"
                else:
                    dur_frac = str(dur_frac).strip()
                events.append(
                    MeasureRepeat(
                        subtype=subtype.strip(),
                        duration_type=dur_type.strip(),
                        duration=dur_frac,
                    )
                )
                continue

            # ---- IGNORE other elements in voice ----
            else:
                continue

    return events, key_sig, time_sig


def _parse_staff_extras(staff_el: ET.Element) -> tuple[dict, ...]:
    """Brackets, StaffType, defaultClef, etc. (everything before first Measure except VBox)."""
    items: list[dict] = []
    for c in staff_el:
        if c.tag == "Measure":
            break
        if c.tag == "VBox":
            continue
        j = element_to_json(c)
        if j is not None:
            items.append(j)
    return tuple(items)


def _parse_staff_vboxes(staff_el: ET.Element) -> tuple[VBoxFrame, ...]:
    frames: list[VBoxFrame] = []
    for child in staff_el:
        if child.tag == "Measure":
            break
        if child.tag != "VBox":
            continue
        texts: list[FrameText] = []
        for t_el in child.findall("Text"):
            texts.append(
                FrameText(
                    style=(t_el.findtext("style") or "").strip(),
                    text=(t_el.findtext("text") or "").strip(),
                )
            )
        frames.append(
            VBoxFrame(
                height=_opt_text(child.findtext("height")),
                texts=tuple(texts),
            )
        )
    return tuple(frames)


def parse_staff_measures(staff_el: ET.Element) -> list[Measure]:
    """Parse measures from a Staff XML element (all direct-child <voice> blocks per measure)."""
    measures: list[Measure] = []
    active_slur_starts_by_voice: dict[str, list] = {}
    active_tie_starts_by_voice: dict[str, list] = {}

    for i, measure_el in enumerate(staff_el.findall("Measure"), start=1):
        irregular = None
        irregular_el = measure_el.find("irregular")
        if irregular_el is not None and irregular_el.text is not None:
            try:
                irregular = float(irregular_el.text)
            except ValueError:
                pass

        measure_len = measure_el.get("len")
        measure_repeat_count = _parse_measure_repeat_count(measure_el)
        double_bar = _measure_has_double_barline(measure_el)

        layout_breaks: list[LayoutBreak] = []
        for c in measure_el:
            if c.tag == "LayoutBreak":
                st = (c.findtext("subtype") or "").strip()
                if st:
                    layout_breaks.append(LayoutBreak(subtype=st))
        layout_breaks_t = tuple(layout_breaks)

        voice_children = [c for c in measure_el if c.tag == "voice"]
        if not voice_children:
            measures.append(
                Measure(
                    number=i,
                    voices={"0": []},
                    key_sig=None,
                    time_sig=None,
                    irregular=irregular,
                    measure_len=measure_len,
                    measure_repeat_count=measure_repeat_count,
                    double_bar=double_bar,
                    layout_breaks=layout_breaks_t,
                )
            )
            continue

        voices_out: dict[str, list[Event]] = {}
        measure_key_sig = None
        measure_time_sig = None

        for vi, voice_el in enumerate(voice_children):
            vk = str(vi)
            if vk not in active_slur_starts_by_voice:
                active_slur_starts_by_voice[vk] = []
                active_tie_starts_by_voice[vk] = []
            evs, ksig, tsig = _parse_single_voice_content(
                voice_el,
                active_slur_starts_by_voice[vk],
                active_tie_starts_by_voice[vk],
            )
            voices_out[vk] = evs
            if measure_key_sig is None and ksig is not None:
                measure_key_sig = ksig
            if measure_time_sig is None and tsig is not None:
                measure_time_sig = tsig

        measures.append(
            Measure(
                number=i,
                voices=voices_out,
                key_sig=measure_key_sig,
                time_sig=measure_time_sig,
                irregular=irregular,
                measure_len=measure_len,
                measure_repeat_count=measure_repeat_count,
                double_bar=double_bar,
                layout_breaks=layout_breaks_t,
            )
        )

    return measures


def parse_score(tree: ET.ElementTree) -> Score:
    """Parse an MSCX ElementTree into a Score object.
    
    This function extracts all musical content from a MuseScore XML file,
    including parts, measures, notes, rests, dynamics, hairpins (cresc./dim.),
    key signatures, time signatures, slurs, and ties.
    
    Args:
        tree: ElementTree representing the MSCX file (typically obtained
            from extract_mscx())
        
    Returns:
        Score object containing all parsed parts and measures
        
    Example:
        >>> from scoreforge.io import extract_mscx
        >>> from pathlib import Path
        >>> tree = extract_mscx(Path("score.mscz"))
        >>> score = parse_score(tree)
        >>> print(f"Parsed {len(score.parts)} parts")
    """
    root = tree.getroot()
    score_el = root.find("Score")
    if score_el is None:
        return Score(parts=[])

    meta_tags: dict[str, str] = {}
    for mt in score_el.findall("metaTag"):
        name = mt.get("name")
        if name:
            meta_tags[name] = (mt.text or "").strip()

    div_txt = score_el.findtext("Division")
    division = _opt_int(div_txt) if div_txt is not None else None

    order_el = score_el.find("Order")
    order_tree = element_to_json(order_el)

    part_definitions = tuple(
        element_to_json(p) for p in score_el.findall("Part")
    )

    parts: list[Part] = []

    for staff_el in score_el.findall("Staff"):
        measures = parse_staff_measures(staff_el)
        vbox_frames = _parse_staff_vboxes(staff_el)
        staff_extras = _parse_staff_extras(staff_el)
        parts.append(
            Part(
                part_id=staff_el.get("id"),
                measures=measures,
                vbox_frames=vbox_frames,
                staff_extras=staff_extras,
            )
        )

    return Score(
        parts=parts,
        muse_score_version=root.get("version"),
        division=division,
        program_version=_opt_text(root.findtext("programVersion")),
        program_revision=_opt_text(root.findtext("programRevision")),
        show_invisible=_opt_int(score_el.findtext("showInvisible")),
        show_unprintable=_opt_int(score_el.findtext("showUnprintable")),
        show_frames=_opt_int(score_el.findtext("showFrames")),
        show_margins=_opt_int(score_el.findtext("showMargins")),
        score_open=_opt_int(score_el.findtext("open")),
        meta_tags=meta_tags,
        order_tree=order_tree,
        part_definitions=part_definitions,
    )
