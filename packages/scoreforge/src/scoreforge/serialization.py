import json
from pathlib import Path

from scoreforge.models import (
    Score,
    Part,
    Measure,
    Event,
    Note,
    Rest,
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
    Lyric,
    HairpinStart,
    HairpinEnd,
    OttavaStart,
    OttavaEnd,
    StaffText,
    RehearsalMark,
    Tempo,
    InstrumentChange,
    LayoutBreak,
    VBoxFrame,
    FrameText,
)


def _lyrics_to_json(lyrics: tuple[Lyric, ...]) -> list[dict]:
    out: list[dict] = []
    for ly in lyrics:
        d: dict = {"text": ly.text}
        if ly.syllabic is not None:
            d["syllabic"] = ly.syllabic
        if ly.ticks_f is not None:
            d["ticksF"] = ly.ticks_f
        if ly.verse is not None:
            d["verse"] = ly.verse
        out.append(d)
    return out


def _lyrics_from_json(raw: object) -> tuple[Lyric, ...]:
    if not isinstance(raw, list) or not raw:
        return ()
    out: list[Lyric] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tf = item.get("ticksF")
        if tf is None:
            tf = item.get("ticks_f")
        v = item.get("verse")
        verse: int | None = None
        if v is not None:
            verse = int(v)
        syl = item.get("syllabic")
        out.append(
            Lyric(
                text=str(item.get("text", "")),
                syllabic=str(syl) if syl is not None else None,
                ticks_f=str(tf) if tf is not None else None,
                verse=verse,
            )
        )
    return tuple(out)


def _serialize_events_list(events: list[Event]) -> list[dict]:
    """Convert canonical events to JSON-serializable dicts."""
    out: list[dict] = []
    for e in events:
        if isinstance(e, Note):
            event_obj = {
                "type": "note",
                "pitch": e.pitch,
                "duration": e.duration,
            }
            if e.dots > 0:
                event_obj["dots"] = e.dots
            if e.stem_direction is not None:
                event_obj["stemDirection"] = e.stem_direction
            if e.no_stem:
                event_obj["noStem"] = True
            if e.articulations:
                event_obj["articulations"] = list(e.articulations)
            if e.tpc is not None:
                event_obj["tpc"] = e.tpc
            if e.symbols:
                event_obj["symbols"] = list(e.symbols)
            if e.head is not None:
                event_obj["head"] = e.head
            if e.play is not None:
                event_obj["play"] = e.play
            if e.fixed is not None:
                event_obj["fixed"] = e.fixed
            if e.fixed_line is not None:
                event_obj["fixedLine"] = e.fixed_line
            if e.slur_start is not None:
                event_obj["slurStart"] = {
                    "nextFractions": e.slur_start.next_fractions,
                }
            if e.slur_end is not None:
                event_obj["slurEnd"] = {
                    "prevFractions": e.slur_end.prev_fractions,
                }
            if e.tie_start is not None:
                event_obj["tieStart"] = {
                    "nextFractions": e.tie_start.next_fractions,
                }
            if e.tie_end is not None:
                event_obj["tieEnd"] = {
                    "prevFractions": e.tie_end.prev_fractions,
                }
            if e.lyrics:
                event_obj["lyrics"] = _lyrics_to_json(e.lyrics)
            out.append(event_obj)
        elif isinstance(e, ChordGroup):
            event_obj = {
                "type": "chord",
                "duration": e.duration,
                "notes": [],
            }
            if e.dots > 0:
                event_obj["dots"] = e.dots
            if e.stem_direction is not None:
                event_obj["stemDirection"] = e.stem_direction
            if e.no_stem:
                event_obj["noStem"] = True
            if e.articulations:
                event_obj["articulations"] = list(e.articulations)
            if e.slur_start is not None:
                event_obj["slurStart"] = {
                    "nextFractions": e.slur_start.next_fractions,
                }
            if e.slur_end is not None:
                event_obj["slurEnd"] = {
                    "prevFractions": e.slur_end.prev_fractions,
                }
            for cn in e.notes:
                nd: dict = {"pitch": cn.pitch}
                if cn.tpc is not None:
                    nd["tpc"] = cn.tpc
                if cn.symbols:
                    nd["symbols"] = list(cn.symbols)
                if cn.head is not None:
                    nd["head"] = cn.head
                if cn.play is not None:
                    nd["play"] = cn.play
                if cn.fixed is not None:
                    nd["fixed"] = cn.fixed
                if cn.fixed_line is not None:
                    nd["fixedLine"] = cn.fixed_line
                if cn.tie_start is not None:
                    nd["tieStart"] = {
                        "nextFractions": cn.tie_start.next_fractions,
                    }
                if cn.tie_end is not None:
                    nd["tieEnd"] = {
                        "prevFractions": cn.tie_end.prev_fractions,
                    }
                event_obj["notes"].append(nd)
            if e.lyrics:
                event_obj["lyrics"] = _lyrics_to_json(e.lyrics)
            out.append(event_obj)
        elif isinstance(e, Rest):
            event_obj = {
                "type": "rest",
                "duration": e.duration,
            }
            if e.dots > 0:
                event_obj["dots"] = e.dots
            if e.measure_duration is not None:
                event_obj["measureDuration"] = e.measure_duration
            out.append(event_obj)
        elif isinstance(e, Dynamic):
            d_obj: dict = {
                "type": "dynamic",
                "subtype": e.subtype,
            }
            if e.velocity is not None:
                d_obj["velocity"] = e.velocity
            out.append(d_obj)
        elif isinstance(e, HairpinStart):
            ho: dict = {
                "type": "hairpinStart",
                "subtype": e.subtype,
            }
            if e.next_measures is not None:
                ho["nextMeasures"] = e.next_measures
            if e.next_fractions is not None:
                ho["nextFractions"] = e.next_fractions
            if e.direction is not None:
                ho["direction"] = e.direction
            out.append(ho)
        elif isinstance(e, HairpinEnd):
            he: dict = {"type": "hairpinEnd"}
            if e.prev_measures is not None:
                he["prevMeasures"] = e.prev_measures
            if e.prev_fractions is not None:
                he["prevFractions"] = e.prev_fractions
            out.append(he)
        elif isinstance(e, MeasureRepeat):
            out.append({
                "type": "measureRepeat",
                "subtype": e.subtype,
                "durationType": e.duration_type,
                "duration": e.duration,
            })
        elif isinstance(e, OttavaStart):
            oo: dict = {
                "type": "ottavaStart",
                "subtype": e.subtype,
            }
            if e.next_measures is not None:
                oo["nextMeasures"] = e.next_measures
            if e.next_fractions is not None:
                oo["nextFractions"] = e.next_fractions
            out.append(oo)
        elif isinstance(e, OttavaEnd):
            oe: dict = {"type": "ottavaEnd"}
            if e.prev_measures is not None:
                oe["prevMeasures"] = e.prev_measures
            if e.prev_fractions is not None:
                oe["prevFractions"] = e.prev_fractions
            out.append(oe)
        elif isinstance(e, StaffText):
            out.append({"type": "staffText", "text": e.text})
        elif isinstance(e, RehearsalMark):
            out.append({"type": "rehearsalMark", "text": e.text})
        elif isinstance(e, Tempo):
            td: dict = {
                "type": "tempo",
                "text": e.text,
                "tempo": e.tempo,
            }
            if e.follow_text is not None:
                td["followText"] = e.follow_text
            out.append(td)
        elif isinstance(e, InstrumentChange):
            out.append({
                "type": "instrumentChange",
                "text": e.text,
                "init": e.init,
                "instrument": e.instrument_tree,
            })
        else:
            raise TypeError(f"Unknown event type: {type(e)}")
    return out


def save_canonical(score: Score, path: Path) -> None:
    """Save a Score object to a canonical JSON file.
    
    Serializes a Score object to the ScoreForge canonical JSON format.
    This format is designed for version control and text-based diffing,
    with a structure that minimizes merge conflicts.
    
    The JSON format uses dictionaries keyed by part_id and measure number,
    making it easy to see changes at the measure level.
    
    Args:
        score: Score object to serialize
        path: Path where the JSON file should be written
        
    Example:
        >>> from scoreforge.parser import parse_score
        >>> from scoreforge.io import extract_mscx
        >>> from pathlib import Path
        >>> tree = extract_mscx(Path("score.mscz"))
        >>> score = parse_score(tree)
        >>> save_canonical(score, Path("score.json"))
    """
    obj: dict = {
        "score_id": score.score_id if score.score_id is not None else "",
        "parts": {},
    }

    if score.muse_score_version is not None:
        obj["museScoreVersion"] = score.muse_score_version
    if score.division is not None:
        obj["division"] = score.division
    if score.program_version is not None:
        obj["programVersion"] = score.program_version
    if score.program_revision is not None:
        obj["programRevision"] = score.program_revision
    if score.show_invisible is not None:
        obj["showInvisible"] = score.show_invisible
    if score.show_unprintable is not None:
        obj["showUnprintable"] = score.show_unprintable
    if score.show_frames is not None:
        obj["showFrames"] = score.show_frames
    if score.show_margins is not None:
        obj["showMargins"] = score.show_margins
    if score.score_open is not None:
        obj["open"] = score.score_open
    if score.meta_tags:
        obj["metaTags"] = dict(sorted(score.meta_tags.items()))
    if score.order_tree is not None:
        obj["order"] = score.order_tree
    if score.part_definitions:
        obj["partDefinitions"] = list(score.part_definitions)

    for part in score.parts:
        measures_dict = {}
        part_entry: dict = {"measures": measures_dict}

        if part.vbox_frames:
            part_entry["vbox"] = [
                {
                    "height": vf.height,
                    "texts": [{"style": ft.style, "text": ft.text} for ft in vf.texts],
                }
                for vf in part.vbox_frames
            ]

        if part.staff_extras:
            part_entry["staffExtras"] = list(part.staff_extras)

        for measure in part.measures:
            meas_obj: dict = {}

            if measure.irregular is not None:
                meas_obj["irregular"] = measure.irregular

            if measure.measure_len is not None:
                meas_obj["len"] = measure.measure_len

            if measure.key_sig is not None:
                ks_out: dict = {}
                if measure.key_sig.concert_key is not None:
                    ks_out["concertKey"] = measure.key_sig.concert_key
                if measure.key_sig.custom is not None:
                    ks_out["custom"] = measure.key_sig.custom
                if measure.key_sig.mode is not None:
                    ks_out["mode"] = measure.key_sig.mode
                if ks_out:
                    meas_obj["keySig"] = ks_out

            if measure.time_sig is not None:
                meas_obj["timeSig"] = {
                    "sigN": measure.time_sig.sig_n,
                    "sigD": measure.time_sig.sig_d,
                }

            if measure.measure_repeat_count is not None:
                meas_obj["measureRepeatCount"] = measure.measure_repeat_count

            if measure.double_bar:
                meas_obj["doubleBar"] = True

            if measure.layout_breaks:
                meas_obj["layoutBreaks"] = [
                    {"subtype": lb.subtype} for lb in measure.layout_breaks
                ]

            if not measure.voices:
                meas_obj["events"] = []
            elif set(measure.voices.keys()) == {"0"}:
                meas_obj["events"] = _serialize_events_list(measure.voices["0"])
            else:
                meas_obj["voices"] = {}
                for vk in sorted(measure.voices.keys(), key=int):
                    meas_obj["voices"][vk] = {
                        "events": _serialize_events_list(measure.voices[vk]),
                    }

            measures_dict[str(measure.number)] = meas_obj

        obj["parts"][part.part_id] = part_entry

    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _measure_keys_sorted_numeric(measures_data: dict) -> list[str]:
    """Iterate measure keys in score order (1,2,…,9,10,…), not lexicographic."""
    return sorted(measures_data.keys(), key=lambda k: int(k))


def load_score_from_json(path: Path) -> Score:
    """Load a Score object from a canonical JSON file.
    
    Deserializes a Score object from the ScoreForge canonical JSON format.
    Supports both the current format (dictionaries) and legacy formats
    (lists) for backward compatibility.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Score object deserialized from the JSON file, ready for
        conversion to MSCX or merging with other scores
        
    Example:
        >>> from pathlib import Path
        >>> from scoreforge.converter import score_to_mscx
        >>> from scoreforge.io import write_mscz
        >>> score = load_score_from_json(Path("score.json"))
        >>> tree = score_to_mscx(score)
        >>> write_mscz(tree, Path("output.mscz"))
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get score_id, defaulting to None if not present (for backward compatibility)
    score_id = data.get("score_id")
    if score_id == "":
        score_id = None

    def _vbox_from_data(raw: object) -> tuple[VBoxFrame, ...]:
        if not isinstance(raw, list):
            return ()
        frames: list[VBoxFrame] = []
        for vb in raw:
            if not isinstance(vb, dict):
                continue
            texts = tuple(
                FrameText(style=str(t.get("style", "")), text=str(t.get("text", "")))
                for t in vb.get("texts", [])
                if isinstance(t, dict)
            )
            frames.append(
                VBoxFrame(
                    height=vb.get("height"),
                    texts=texts,
                )
            )
        return tuple(frames)

    def _staff_extras_from_data(raw: object) -> tuple[dict, ...]:
        if not isinstance(raw, list):
            return ()
        return tuple(x for x in raw if isinstance(x, dict))

    parts: list[Part] = []

    # Handle both old format (list) and new format (dict)
    parts_data = data.get("parts", {})
    if isinstance(parts_data, list):
        # Old format: list of parts
        for part_data in parts_data:
            measures: list[Measure] = []
            measures_data = part_data.get("measures", [])
            
            if isinstance(measures_data, list):
                # Old format: list of measures
                for measure_data in measures_data:
                    measure_number = int(measure_data.get("number", 0))
                    measures.append(_parse_measure(measure_data, measure_number))
            else:
                # New format: dict of measures
                for measure_num_str in _measure_keys_sorted_numeric(measures_data):
                    measure_data = measures_data[measure_num_str]
                    measure_number = int(measure_num_str)
                    measures.append(_parse_measure(measure_data, measure_number))
            
            parts.append(
                Part(
                    part_id=part_data.get("id", ""),
                    measures=measures,
                    vbox_frames=_vbox_from_data(part_data.get("vbox")),
                )
            )
    else:
        # New format: dict of parts
        for part_id, part_data in parts_data.items():
            measures: list[Measure] = []
            measures_data = part_data.get("measures", {})
            
            for measure_num_str in _measure_keys_sorted_numeric(measures_data):
                measure_data = measures_data[measure_num_str]
                measure_number = int(measure_num_str)
                measures.append(_parse_measure(measure_data, measure_number))
            
            parts.append(
                Part(
                    part_id=part_id,
                    measures=measures,
                    vbox_frames=_vbox_from_data(part_data.get("vbox")),
                    staff_extras=_staff_extras_from_data(part_data.get("staffExtras")),
                )
            )

    order_tree = data.get("order")
    if not isinstance(order_tree, dict):
        order_tree = None

    pd_raw = data.get("partDefinitions")
    if isinstance(pd_raw, list):
        part_definitions = tuple(x for x in pd_raw if isinstance(x, dict))
    else:
        part_definitions = ()

    mt = data.get("metaTags")
    meta_tags = dict(mt) if isinstance(mt, dict) else {}

    return Score(
        parts=parts,
        score_id=score_id,
        muse_score_version=data.get("museScoreVersion"),
        division=data.get("division"),
        program_version=data.get("programVersion"),
        program_revision=data.get("programRevision"),
        show_invisible=data.get("showInvisible"),
        show_unprintable=data.get("showUnprintable"),
        show_frames=data.get("showFrames"),
        show_margins=data.get("showMargins"),
        score_open=data.get("open"),
        meta_tags=meta_tags,
        order_tree=order_tree,
        part_definitions=part_definitions,
    )


def _chord_note_from_json(nd: dict) -> ChordNote:
    ts = None
    if "tieStart" in nd:
        ts = TieStart(next_fractions=nd["tieStart"]["nextFractions"])
    te = None
    if "tieEnd" in nd:
        te = TieEnd(prev_fractions=nd["tieEnd"]["prevFractions"])
    fl = nd.get("fixedLine")
    tpc = nd.get("tpc")
    return ChordNote(
        pitch=nd["pitch"],
        tie_start=ts,
        tie_end=te,
        tpc=int(tpc) if tpc is not None else None,
        symbols=tuple(nd.get("symbols") or ()),
        head=nd.get("head"),
        play=nd.get("play"),
        fixed=nd.get("fixed"),
        fixed_line=int(fl) if fl is not None else None,
    )


def _parse_events_from_json_list(event_data_list: list) -> list[Event]:
    events: list[Event] = []
    for event_data in event_data_list:
        event_type = event_data.get("type")
        dots = int(event_data.get("dots", 0))
        dots = max(0, min(2, dots))

        if event_type == "note" or (
            "pitch" in event_data
            and event_type != "chord"
            and "notes" not in event_data
        ):
            if "duration" not in event_data:
                continue
            slur_start = None
            if "slurStart" in event_data:
                slur_data = event_data["slurStart"]
                slur_start = SlurStart(
                    next_fractions=slur_data["nextFractions"],
                )
            slur_end = None
            if "slurEnd" in event_data:
                slur_data = event_data["slurEnd"]
                slur_end = SlurEnd(
                    prev_fractions=slur_data["prevFractions"],
                )

            tie_start = None
            if "tieStart" in event_data:
                tie_data = event_data["tieStart"]
                tie_start = TieStart(
                    next_fractions=tie_data["nextFractions"],
                )
            tie_end = None
            if "tieEnd" in event_data:
                tie_data = event_data["tieEnd"]
                tie_end = TieEnd(
                    prev_fractions=tie_data["prevFractions"],
                )

            cn = _chord_note_from_json(
                {
                    "pitch": event_data["pitch"],
                    **{
                        k: event_data[k]
                        for k in (
                            "tpc",
                            "symbols",
                            "head",
                            "play",
                            "fixed",
                            "fixedLine",
                        )
                        if k in event_data
                    },
                }
            )
            arts = tuple(event_data.get("articulations") or ())
            events.append(
                Note(
                    pitch=event_data["pitch"],
                    duration=float(event_data["duration"]),
                    dots=dots,
                    slur_start=slur_start,
                    slur_end=slur_end,
                    tie_start=tie_start,
                    tie_end=tie_end,
                    stem_direction=event_data.get("stemDirection"),
                    no_stem=bool(event_data.get("noStem")),
                    articulations=arts,
                    tpc=cn.tpc,
                    symbols=cn.symbols,
                    head=cn.head,
                    play=cn.play,
                    fixed=cn.fixed,
                    fixed_line=cn.fixed_line,
                    lyrics=_lyrics_from_json(event_data.get("lyrics")),
                )
            )
        elif event_type == "chord":
            slur_start = None
            if "slurStart" in event_data:
                sd = event_data["slurStart"]
                slur_start = SlurStart(next_fractions=sd["nextFractions"])
            slur_end = None
            if "slurEnd" in event_data:
                sd = event_data["slurEnd"]
                slur_end = SlurEnd(prev_fractions=sd["prevFractions"])
            chord_notes: list[ChordNote] = [
                _chord_note_from_json(nd) for nd in event_data["notes"]
            ]
            events.append(
                ChordGroup(
                    notes=tuple(chord_notes),
                    duration=float(event_data["duration"]),
                    dots=dots,
                    slur_start=slur_start,
                    slur_end=slur_end,
                    stem_direction=event_data.get("stemDirection"),
                    no_stem=bool(event_data.get("noStem")),
                    articulations=tuple(event_data.get("articulations") or ()),
                    lyrics=_lyrics_from_json(event_data.get("lyrics")),
                )
            )
        elif event_type == "rest":
            md = event_data.get("measureDuration")
            events.append(
                Rest(
                    duration=float(event_data["duration"]),
                    dots=dots,
                    measure_duration=md,
                )
            )
        elif event_type == "dynamic":
            vel = event_data.get("velocity")
            events.append(
                Dynamic(
                    subtype=event_data["subtype"],
                    velocity=int(vel) if vel is not None else None,
                )
            )
        elif event_type == "hairpinStart":
            events.append(
                HairpinStart(
                    subtype=str(event_data["subtype"]),
                    next_measures=event_data.get("nextMeasures"),
                    next_fractions=event_data.get("nextFractions"),
                    direction=event_data.get("direction"),
                )
            )
        elif event_type == "hairpinEnd":
            events.append(
                HairpinEnd(
                    prev_measures=event_data.get("prevMeasures"),
                    prev_fractions=event_data.get("prevFractions"),
                )
            )
        elif event_type == "measureRepeat":
            events.append(
                MeasureRepeat(
                    subtype=str(event_data["subtype"]),
                    duration_type=str(event_data.get("durationType", "measure")),
                    duration=str(event_data["duration"]),
                )
            )
        elif event_type == "ottavaStart":
            events.append(
                OttavaStart(
                    subtype=str(event_data.get("subtype") or "8va"),
                    next_measures=event_data.get("nextMeasures"),
                    next_fractions=event_data.get("nextFractions"),
                )
            )
        elif event_type == "ottavaEnd":
            events.append(
                OttavaEnd(
                    prev_measures=event_data.get("prevMeasures"),
                    prev_fractions=event_data.get("prevFractions"),
                )
            )
        elif event_type == "staffText":
            events.append(StaffText(text=str(event_data.get("text", ""))))
        elif event_type == "rehearsalMark":
            events.append(RehearsalMark(text=str(event_data.get("text", ""))))
        elif event_type == "tempo":
            ft = event_data.get("followText")
            if ft is not None:
                ft = str(ft)
            events.append(
                Tempo(
                    text=str(event_data.get("text", "")),
                    tempo=str(event_data.get("tempo", "1")),
                    follow_text=ft,
                )
            )
        elif event_type == "instrumentChange":
            inst = event_data.get("instrument")
            if not isinstance(inst, dict):
                inst = {"tag": "Instrument"}
            ir_init = event_data.get("init")
            if ir_init is not None:
                ir_init = str(ir_init)
            events.append(
                InstrumentChange(
                    text=str(event_data.get("text", "")),
                    init=ir_init,
                    instrument_tree=inst,
                )
            )
        else:
            if "pitch" in event_data and "duration" in event_data:
                slur_start = None
                if "slurStart" in event_data:
                    slur_data = event_data["slurStart"]
                    slur_start = SlurStart(
                        next_fractions=slur_data["nextFractions"],
                    )
                slur_end = None
                if "slurEnd" in event_data:
                    slur_data = event_data["slurEnd"]
                    slur_end = SlurEnd(
                        prev_fractions=slur_data["prevFractions"],
                    )

                tie_start = None
                if "tieStart" in event_data:
                    tie_data = event_data["tieStart"]
                    tie_start = TieStart(
                        next_fractions=tie_data["nextFractions"],
                    )
                tie_end = None
                if "tieEnd" in event_data:
                    tie_data = event_data["tieEnd"]
                    tie_end = TieEnd(
                        prev_fractions=tie_data["prevFractions"],
                    )

                cn = _chord_note_from_json(
                    {
                        "pitch": event_data["pitch"],
                        **{
                            k: event_data[k]
                            for k in (
                                "tpc",
                                "symbols",
                                "head",
                                "play",
                                "fixed",
                                "fixedLine",
                            )
                            if k in event_data
                        },
                    }
                )
                events.append(
                    Note(
                        pitch=event_data["pitch"],
                        duration=float(event_data["duration"]),
                        dots=dots,
                        slur_start=slur_start,
                        slur_end=slur_end,
                        tie_start=tie_start,
                        tie_end=tie_end,
                        stem_direction=event_data.get("stemDirection"),
                        no_stem=bool(event_data.get("noStem")),
                        articulations=tuple(event_data.get("articulations") or ()),
                        tpc=cn.tpc,
                        symbols=cn.symbols,
                        head=cn.head,
                        play=cn.play,
                        fixed=cn.fixed,
                        fixed_line=cn.fixed_line,
                        lyrics=_lyrics_from_json(event_data.get("lyrics")),
                    )
                )
            elif "duration" in event_data:
                md = event_data.get("measureDuration")
                events.append(
                    Rest(
                        duration=float(event_data["duration"]),
                        dots=dots,
                        measure_duration=md,
                    )
                )
    return events


def _parse_measure(measure_data: dict, measure_number: int) -> Measure:
    """Parse a measure from JSON data.
    
    Args:
        measure_data: Dictionary containing measure data
        measure_number: The measure number (extracted from key in new format)
        
    Returns:
        Measure object
    """
    # Parse irregular measure length if present
    irregular = None
    if "irregular" in measure_data:
        irregular = float(measure_data["irregular"])

    # Parse measure length when different from time sig (e.g. "1/4" for pickup)
    measure_len = measure_data.get("len")

    # Parse KeySig if present
    key_sig = None
    if "keySig" in measure_data:
        kd = measure_data["keySig"]
        ck = kd.get("concertKey")
        cu = kd.get("custom")
        mode = kd.get("mode")
        key_sig = KeySig(
            concert_key=int(ck) if ck is not None else None,
            custom=int(cu) if cu is not None else None,
            mode=str(mode) if mode is not None else None,
        )
        if (
            key_sig.concert_key is None
            and key_sig.custom is None
            and key_sig.mode is None
        ):
            key_sig = None
    
    # Parse TimeSig if present
    time_sig = None
    if "timeSig" in measure_data:
        time_sig_data = measure_data["timeSig"]
        time_sig = TimeSig(
            sig_n=int(time_sig_data["sigN"]),
            sig_d=int(time_sig_data["sigD"]),
        )

    measure_repeat_count = measure_data.get("measureRepeatCount")
    if measure_repeat_count is not None:
        measure_repeat_count = int(measure_repeat_count)

    double_bar = bool(measure_data.get("doubleBar", False))

    layout_breaks: tuple[LayoutBreak, ...] = ()
    lb_raw = measure_data.get("layoutBreaks")
    if isinstance(lb_raw, list):
        layout_breaks = tuple(
            LayoutBreak(subtype=str(x.get("subtype", "")))
            for x in lb_raw
            if isinstance(x, dict) and x.get("subtype")
        )

    if "voices" in measure_data:
        voices: dict[str, list[Event]] = {}
        for vk in sorted(measure_data["voices"].keys(), key=int):
            ved = measure_data["voices"][vk]
            voices[str(vk)] = _parse_events_from_json_list(ved.get("events", []))
    elif "events" in measure_data:
        voices = {"0": _parse_events_from_json_list(measure_data["events"])}
    else:
        voices = {}

    return Measure(
        number=measure_number,
        voices=voices,
        key_sig=key_sig,
        time_sig=time_sig,
        irregular=irregular,
        measure_len=measure_len,
        measure_repeat_count=measure_repeat_count,
        double_bar=double_bar,
        layout_breaks=layout_breaks,
    )

