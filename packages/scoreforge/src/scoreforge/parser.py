"""XML parsing for MSCX files."""

import xml.etree.ElementTree as ET

from scoreforge.models import (
    Score, Note, Measure, Part, Rest, Event, KeySig, TimeSig, Dynamic,
    SlurStart, SlurEnd, TieStart, TieEnd
)
from scoreforge.converter import midi_to_pitch


# Duration mapping from MSCX format to numeric values
DURATION_MAP = {
    "whole": 4,
    "half": 2,
    "quarter": 1,
    "eighth": 0.5,
    # TODO: Fill this in more
}


def parse_staff_measures(staff_el: ET.Element) -> list[Measure]:
    """Parse measures from a Staff XML element.
    
    Args:
        staff_el: Staff XML element
        
    Returns:
        List of Measure objects
    """
    measures: list[Measure] = []

    # Track slur and tie starts across all measures in this staff
    # This allows matching start/end pairs that span multiple measures
    active_slur_starts = []  # Stack of slur start offsets (for nested slurs)
    active_tie_starts = []  # List of tie start offsets (for matching)

    for i, measure_el in enumerate(staff_el.findall("Measure"), start=1):
        events: list[Event] = []
        key_sig = None
        time_sig = None
        
        # Parse irregular measure length if present (pickup measures, etc.)
        irregular = None
        irregular_el = measure_el.find("irregular")
        if irregular_el is not None:
            irregular_text = irregular_el.text
            if irregular_text is not None:
                try:
                    irregular = float(irregular_text)
                except ValueError:
                    pass

        # Parse measure length when different from time signature (e.g. len="1/4" for pickup)
        measure_len = measure_el.get("len")

        voice_el = measure_el.find("voice")
        if voice_el is None:
            measures.append(
                Measure(
                    number=i,
                    events=[],
                    key_sig=key_sig,
                    time_sig=time_sig,
                    irregular=irregular,
                    measure_len=measure_len,
                )
            )
            continue

        # Parse KeySig and TimeSig from voice element
        for el in list(voice_el):
            # ---- KEYSIG ----
            if el.tag == "KeySig":
                concert_key_text = el.findtext("concertKey")
                if concert_key_text is not None:
                    key_sig = KeySig(
                        concert_key=int(concert_key_text),
                    )
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
                
                # Parse dots
                dots_text = el.findtext("dots", "0")
                try:
                    dots = int(dots_text)
                except ValueError:
                    dots = 0
                # Clamp dots to valid range (0-2)
                dots = max(0, min(2, dots))

                # Parse slur information from Chord
                slur_start = None
                slur_end = None
                for spanner_el in el.findall("Spanner"):
                    if spanner_el.get("type") == "Slur":
                        # Check for next (start of slur)
                        next_el = spanner_el.find("next")
                        if next_el is not None:
                            location_el = next_el.find("location")
                            if location_el is not None:
                                fractions = location_el.findtext("fractions")
                                if fractions:
                                    slur_start = SlurStart(next_fractions=fractions)
                                    # Track this slur start for matching with end
                                    active_slur_starts.append(fractions)
                        
                        # Check for prev (end of slur) - typically does NOT have Slur element
                        prev_el = spanner_el.find("prev")
                        if prev_el is not None:
                            location_el = prev_el.find("location")
                            if location_el is not None:
                                fractions = location_el.findtext("fractions")
                                if fractions:
                                    # Match with the most recent slur start
                                    if active_slur_starts:
                                        # Remove the matched start from the list
                                        active_slur_starts.pop()
                                    slur_end = SlurEnd(prev_fractions=fractions)

                notes = []
                for note_el in el.findall("Note"):
                    pitch = int(note_el.findtext("pitch"))
                    
                    # Parse tie information from Note
                    tie_start = None
                    tie_end = None
                    for spanner_el in note_el.findall("Spanner"):
                        if spanner_el.get("type") == "Tie":
                            # Check for next (start of tie)
                            next_el = spanner_el.find("next")
                            if next_el is not None:
                                location_el = next_el.find("location")
                                if location_el is not None:
                                    # Check for fractions (within measure) or measures (across measures)
                                    fractions = location_el.findtext("fractions")
                                    measures_offset = location_el.findtext("measures")
                                    offset = fractions if fractions else measures_offset
                                    if offset:
                                        tie_start = TieStart(next_fractions=offset)
                                        # Track this tie start for matching with end
                                        active_tie_starts.append(offset)
                            
                            # Check for prev (end of tie) - typically does NOT have Tie element
                            prev_el = spanner_el.find("prev")
                            if prev_el is not None:
                                location_el = prev_el.find("location")
                                if location_el is not None:
                                    # Check for fractions (within measure) or measures (across measures)
                                    fractions = location_el.findtext("fractions")
                                    measures_offset = location_el.findtext("measures")
                                    offset = fractions if fractions else measures_offset
                                    if offset:
                                        # Match with the most recent tie start
                                        if active_tie_starts:
                                            # Remove the matched start from the list
                                            active_tie_starts.pop()
                                        tie_end = TieEnd(prev_fractions=offset)
                    
                    notes.append(
                        Note(
                            pitch=midi_to_pitch(pitch),
                            duration=base_duration,  # Store base duration
                            dots=dots,  # Store dots separately
                            slur_start=slur_start,
                            slur_end=slur_end,
                            tie_start=tie_start,
                            tie_end=tie_end,
                        )
                    )

                # v0: flatten single-note chords
                events.extend(notes)

            # ---- REST ----
            elif el.tag == "Rest":
                dur_type = el.findtext("durationType", "quarter")
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
                        Dynamic(subtype=subtype)
                    )
                continue

            # ---- IGNORE other elements in voice ----
            else:
                continue

        measures.append(
            Measure(
                number=i,
                events=events,
                key_sig=key_sig,
                time_sig=time_sig,
                irregular=irregular,
                measure_len=measure_len,
            )
        )

    return measures


def parse_score(tree: ET.ElementTree) -> Score:
    """Parse an MSCX ElementTree into a Score object.
    
    This function extracts all musical content from a MuseScore XML file,
    including parts, measures, notes, rests, dynamics, key signatures,
    time signatures, slurs, and ties.
    
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

    parts: list[Part] = []

    for staff_el in score_el.findall("Staff"):
        measures = parse_staff_measures(staff_el)
        parts.append(
            Part(
                part_id=staff_el.get("id"),
                measures=measures,
            )
        )

    return Score(parts=parts)
