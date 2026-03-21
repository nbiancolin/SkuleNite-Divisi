import json
from pathlib import Path

from scoreforge.models import (
    Score, Part, Measure, Event, Note, Rest, KeySig, TimeSig, Dynamic,
    SlurStart, SlurEnd, TieStart, TieEnd, MeasureRepeat,
    ChordGroup, ChordNote,
    HairpinStart, HairpinEnd,
)


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
            out.append(event_obj)
        elif isinstance(e, ChordGroup):
            event_obj = {
                "type": "chord",
                "duration": e.duration,
                "notes": [],
            }
            if e.dots > 0:
                event_obj["dots"] = e.dots
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
                if cn.tie_start is not None:
                    nd["tieStart"] = {
                        "nextFractions": cn.tie_start.next_fractions,
                    }
                if cn.tie_end is not None:
                    nd["tieEnd"] = {
                        "prevFractions": cn.tie_end.prev_fractions,
                    }
                event_obj["notes"].append(nd)
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
            out.append({
                "type": "dynamic",
                "subtype": e.subtype,
            })
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
    obj = {
        "score_id": score.score_id if score.score_id is not None else "",
        "parts": {}
    }

    for part in score.parts:
        measures_dict = {}

        for measure in part.measures:
            meas_obj: dict = {}

            if measure.irregular is not None:
                meas_obj["irregular"] = measure.irregular

            if measure.measure_len is not None:
                meas_obj["len"] = measure.measure_len

            if measure.key_sig is not None:
                meas_obj["keySig"] = {
                    "concertKey": measure.key_sig.concert_key,
                }

            if measure.time_sig is not None:
                meas_obj["timeSig"] = {
                    "sigN": measure.time_sig.sig_n,
                    "sigD": measure.time_sig.sig_d,
                }

            if measure.measure_repeat_count is not None:
                meas_obj["measureRepeatCount"] = measure.measure_repeat_count

            if measure.double_bar:
                meas_obj["doubleBar"] = True

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

        obj["parts"][part.part_id] = {
            "measures": measures_dict
        }

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
                )
            )

    return Score(parts=parts, score_id=score_id)


def _parse_events_from_json_list(event_data_list: list) -> list[Event]:
    events: list[Event] = []
    for event_data in event_data_list:
        event_type = event_data.get("type")
        dots = int(event_data.get("dots", 0))
        dots = max(0, min(2, dots))

        if event_type == "note" or "pitch" in event_data:
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

            events.append(
                Note(
                    pitch=event_data["pitch"],
                    duration=float(event_data["duration"]),
                    dots=dots,
                    slur_start=slur_start,
                    slur_end=slur_end,
                    tie_start=tie_start,
                    tie_end=tie_end,
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
            chord_notes: list[ChordNote] = []
            for nd in event_data["notes"]:
                ts = None
                if "tieStart" in nd:
                    ts = TieStart(next_fractions=nd["tieStart"]["nextFractions"])
                te = None
                if "tieEnd" in nd:
                    te = TieEnd(prev_fractions=nd["tieEnd"]["prevFractions"])
                chord_notes.append(
                    ChordNote(pitch=nd["pitch"], tie_start=ts, tie_end=te)
                )
            events.append(
                ChordGroup(
                    notes=tuple(chord_notes),
                    duration=float(event_data["duration"]),
                    dots=dots,
                    slur_start=slur_start,
                    slur_end=slur_end,
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
            events.append(
                Dynamic(
                    subtype=event_data["subtype"],
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
        else:
            if "pitch" in event_data:
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

                events.append(
                    Note(
                        pitch=event_data["pitch"],
                        duration=float(event_data["duration"]),
                        dots=dots,
                        slur_start=slur_start,
                        slur_end=slur_end,
                        tie_start=tie_start,
                        tie_end=tie_end,
                    )
                )
            else:
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
        key_sig_data = measure_data["keySig"]
        key_sig = KeySig(
            concert_key=int(key_sig_data["concertKey"]),
        )
    
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
    )

