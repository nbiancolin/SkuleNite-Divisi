import json
from pathlib import Path

from scoreforge.models import (
    Score, Part, Measure, Event, Note, Rest, KeySig, TimeSig, Dynamic,
    SlurStart, SlurEnd, TieStart, TieEnd
)


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
            meas_obj = {
                "events": []
            }
            
            # Add irregular measure length if present
            if measure.irregular is not None:
                meas_obj["irregular"] = measure.irregular
            
            # Add KeySig if present
            if measure.key_sig is not None:
                meas_obj["keySig"] = {
                    "concertKey": measure.key_sig.concert_key,
                }
            
            # Add TimeSig if present
            if measure.time_sig is not None:
                meas_obj["timeSig"] = {
                    "sigN": measure.time_sig.sig_n,
                    "sigD": measure.time_sig.sig_d,
                }

            for e in measure.events:
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
                    meas_obj["events"].append(event_obj)

                elif isinstance(e, Rest):
                    event_obj = {
                        "type": "rest",
                        "duration": e.duration,
                    }
                    if e.dots > 0:
                        event_obj["dots"] = e.dots
                    meas_obj["events"].append(event_obj)
                
                elif isinstance(e, Dynamic):
                    meas_obj["events"].append({
                        "type": "dynamic",
                        "subtype": e.subtype,
                    })

                else:
                    raise TypeError(f"Unknown event type: {type(e)}")

            # Use measure number as string key
            measures_dict[str(measure.number)] = meas_obj

        obj["parts"][part.part_id] = {
            "measures": measures_dict
        }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


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
                for measure_num_str, measure_data in measures_data.items():
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
            
            for measure_num_str, measure_data in measures_data.items():
                measure_number = int(measure_num_str)
                measures.append(_parse_measure(measure_data, measure_number))
            
            parts.append(
                Part(
                    part_id=part_id,
                    measures=measures,
                )
            )

    return Score(parts=parts, score_id=score_id)


def _parse_measure(measure_data: dict, measure_number: int) -> Measure:
    """Parse a measure from JSON data.
    
    Args:
        measure_data: Dictionary containing measure data
        measure_number: The measure number (extracted from key in new format)
        
    Returns:
        Measure object
    """
    events: list[Event] = []
    
    # Parse irregular measure length if present
    irregular = None
    if "irregular" in measure_data:
        irregular = float(measure_data["irregular"])
    
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

    for event_data in measure_data.get("events", []):
        event_type = event_data.get("type")
        dots = int(event_data.get("dots", 0))
        # Clamp dots to valid range
        dots = max(0, min(2, dots))
        
        # Note
        if event_type == "note" or "pitch" in event_data:
            # Parse slur information
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
            
            # Parse tie information
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
        # Rest
        elif event_type == "rest":
            events.append(
                Rest(
                    duration=float(event_data["duration"]),
                    dots=dots,
                )
            )
        # Dynamic
        elif event_type == "dynamic":
            events.append(
                Dynamic(
                    subtype=event_data["subtype"],
                )
            )
        else:
            # Fallback for old format (no type field)
            if "pitch" in event_data:
                # Parse slur information
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
                
                # Parse tie information
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
                events.append(
                    Rest(
                        duration=float(event_data["duration"]),
                        dots=dots,
                    )
                )

    return Measure(
        number=measure_number,
        events=events,
        key_sig=key_sig,
        time_sig=time_sig,
        irregular=irregular,
    )

