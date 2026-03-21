"""Regression: canonical schema captures MSCX elements used in 10-Mirror-Blue Night.mscx."""

import json
import tempfile
from pathlib import Path

import xml.etree.ElementTree as ET

from scoreforge.models import (
    InstrumentChange,
    OttavaEnd,
    OttavaStart,
    StaffText,
    LayoutBreak,
)
from scoreforge.parser import parse_score
from scoreforge.serialization import load_score_from_json, save_canonical


def _mirror_path() -> Path:
    return Path(__file__).parent / "test-data" / "10-Mirror-Blue Night.mscx"


def test_mirror_score_header_and_definitions():
    tree = ET.parse(_mirror_path())
    score = parse_score(tree)

    assert score.muse_score_version == "4.50"
    assert score.division == 480
    assert score.program_version == "4.5.2"
    assert score.meta_tags.get("workTitle") == "Mirror-Blue Night"
    assert score.order_tree is not None
    assert score.order_tree.get("tag") == "Order"
    assert len(score.part_definitions) == 4


def test_mirror_staff_extras_and_vbox():
    tree = ET.parse(_mirror_path())
    score = parse_score(tree)
    p1 = next(p for p in score.parts if p.part_id == "1")

    assert len(p1.vbox_frames) == 1
    assert p1.vbox_frames[0].texts[0].style == "title"
    assert "Mirror-Blue Night" in p1.vbox_frames[0].texts[0].text

    p2 = next(p for p in score.parts if p.part_id == "2")
    assert any(ex.get("tag") == "StaffType" for ex in p2.staff_extras)
    assert any(ex.get("tag") == "bracket" for ex in p2.staff_extras)


def test_mirror_voice_level_elements():
    tree = ET.parse(_mirror_path())
    score = parse_score(tree)
    p1 = next(p for p in score.parts if p.part_id == "1")

    m4 = p1.measures[3]
    assert any(isinstance(lb, LayoutBreak) for lb in m4.layout_breaks)

    m5 = p1.measures[4]
    ev5 = m5.voices.get("0", [])
    assert any(isinstance(e, InstrumentChange) for e in ev5)

    has_artic = any(
        getattr(e, "articulations", ())
        for e in ev5
        if hasattr(e, "articulations")
    )
    assert has_artic

    has_tpc = False
    for m in p1.measures:
        for evs in m.voices.values():
            for e in evs:
                if hasattr(e, "tpc") and getattr(e, "tpc", None) is not None:
                    has_tpc = True
                if hasattr(e, "notes"):
                    for cn in e.notes:
                        if cn.tpc is not None:
                            has_tpc = True
    assert has_tpc

    p2 = next(p for p in score.parts if p.part_id == "2")
    st_meas = p2.measures[0]
    st = next(e for e in st_meas.voices["0"] if isinstance(e, StaffText))
    assert "Piano" in st.text

    p4 = next(p for p in score.parts if p.part_id == "4")
    start_m = next(
        m
        for m in p4.measures
        if any(isinstance(e, OttavaStart) for e in m.voices.get("0", []))
    )
    assert any(isinstance(e, OttavaStart) for e in start_m.voices["0"])
    end_m = next(
        m
        for m in p4.measures
        if any(isinstance(e, OttavaEnd) for e in m.voices.get("0", []))
    )
    assert any(isinstance(e, OttavaEnd) for e in end_m.voices["0"])


def test_mirror_custom_keysig_on_drum_staff():
    tree = ET.parse(_mirror_path())
    score = parse_score(tree)
    p6 = next(p for p in score.parts if p.part_id == "6")
    m1 = p6.measures[0]
    assert m1.key_sig is not None
    assert m1.key_sig.custom == 1
    assert m1.key_sig.mode == "none"
    assert m1.key_sig.concert_key is None


def test_mirror_json_roundtrip_header_and_staff_extras():
    tree = ET.parse(_mirror_path())
    score = parse_score(tree)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "m.json"
        save_canonical(score, path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["museScoreVersion"] == "4.50"
        assert "metaTags" in data
        assert "order" in data
        assert "partDefinitions" in data
        assert data["parts"]["2"]["staffExtras"]

        score2 = load_score_from_json(path)
        assert score2.meta_tags == score.meta_tags
        assert len(score2.part_definitions) == len(score.part_definitions)
        p1a = next(p for p in score.parts if p.part_id == "1")
        p1b = next(p for p in score2.parts if p.part_id == "1")
        assert p1b.vbox_frames == p1a.vbox_frames
        p2a = next(p for p in score.parts if p.part_id == "2")
        p2b = next(p for p in score2.parts if p.part_id == "2")
        assert p2b.staff_extras == p2a.staff_extras
