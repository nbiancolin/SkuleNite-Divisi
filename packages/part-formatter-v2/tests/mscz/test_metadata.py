"""Tests for score metaTags and VBox header helpers."""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from mscz_formatter.mscz.metadata import (
    CONDUCTOR_SCORE_PART_NAME,
    add_broadway_header,
    add_part_name,
    apply_metadata_and_headers_to_mscx,
    set_score_properties,
)
from mscz_formatter.mscz.format import format_mscz

TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "test-data"
NEW_TEST_SCORE = TEST_DATA_DIR / "New-Test-Score.mscz"


def _meta(score: ET.Element, name: str) -> str | None:
    tag = score.find(f"metaTag[@name='{name}']")
    return None if tag is None else tag.text


def test_set_score_properties_creates_and_updates():
    score = ET.Element("Score")
    existing = ET.SubElement(score, "metaTag")
    existing.set("name", "workTitle")
    existing.text = "Old"

    set_score_properties(
        score,
        {
            "workTitle": "New Title",
            "albumTitle": "Show",
            "trackNum": "3",
            "versionNum": "v1.0.0",
            "composer": "Composer",
            "arranger": "Arranger",
        },
    )

    assert _meta(score, "workTitle") == "New Title"
    assert _meta(score, "albumTitle") == "Show"
    assert _meta(score, "trackNum") == "3"
    assert _meta(score, "versionNum") == "v1.0.0"
    assert _meta(score, "composer") == "Composer"
    assert _meta(score, "arranger") == "Arranger"


def test_add_broadway_and_part_name_to_vbox():
    staff = ET.Element("Staff")
    vbox = ET.SubElement(staff, "VBox")

    add_broadway_header(staff, "12", "Skule Nite")
    add_part_name(staff)

    styles = [
        (t.find("style").text, t.find("text").text)
        for t in vbox.findall("Text")
    ]
    assert ("user_2", "12") in styles
    assert ("user_3", "Skule Nite") in styles
    assert ("instrument_excerpt", CONDUCTOR_SCORE_PART_NAME) in styles

    # Second call should not duplicate instrument_excerpt
    add_part_name(staff)
    excerpt_texts = [
        t
        for t in vbox.findall("Text")
        if t.find("style") is not None and t.find("style").text == "instrument_excerpt"
    ]
    assert len(excerpt_texts) == 1


def test_apply_metadata_and_headers_to_mscx(tmp_path):
    # Extract one root mscx from the sample score
    with zipfile.ZipFile(NEW_TEST_SCORE) as z:
        root_mscx = next(n for n in z.namelist() if n.endswith(".mscx") and "Excerpts" not in n)
        src = tmp_path / "score.mscx"
        src.write_bytes(z.read(root_mscx))

    apply_metadata_and_headers_to_mscx(
        str(src),
        show_title="Show",
        show_number="7",
        version_num="v2.0.0",
        work_title="Song",
        composer="Comp",
        arranger="Arr",
        apply_score_metadata=True,
        apply_broadway_vbox_header=True,
        apply_part_name_in_header=True,
        is_broadway=True,
    )

    tree = ET.parse(src)
    score = tree.getroot().find("Score")
    assert score is not None
    assert _meta(score, "albumTitle") == "Show"
    assert _meta(score, "trackNum") == "7"
    assert _meta(score, "versionNum") == "v2.0.0"
    assert _meta(score, "workTitle") == "Song"
    assert _meta(score, "composer") == "Comp"
    assert _meta(score, "arranger") == "Arr"

    staff = score.find("Staff")
    assert staff is not None
    vbox = staff.find("VBox")
    assert vbox is not None
    styles = {t.find("style").text for t in vbox.findall("Text") if t.find("style") is not None}
    assert "user_2" in styles
    assert "user_3" in styles
    assert "instrument_excerpt" in styles


def test_format_mscz_metadata_only(tmp_path):
    out = tmp_path / "meta.mscz"
    ok = format_mscz(
        str(NEW_TEST_SCORE),
        str(out),
        {},
        {
            "selected_style": "broadway",
            "show_title": "Ensemble",
            "show_number": "1",
            "version_num": "v1.2.3",
            "work_title": "Arrangement",
            "composer": "C",
            "arranger": "A",
            "apply_mss_style": False,
            "apply_part_layout": False,
            "apply_score_metadata": True,
            "apply_broadway_vbox_header": False,
            "apply_part_name_in_header": False,
        },
    )
    assert ok
    assert out.is_file()

    with zipfile.ZipFile(out) as z:
        root_mscx = next(n for n in z.namelist() if n.endswith(".mscx") and "Excerpts" not in n)
        score = ET.fromstring(z.read(root_mscx)).find("Score")
    assert score is not None
    assert _meta(score, "albumTitle") == "Ensemble"
    assert _meta(score, "trackNum") == "1"
    assert _meta(score, "versionNum") == "v1.2.3"
    assert _meta(score, "workTitle") == "Arrangement"
    assert _meta(score, "composer") == "C"
    assert _meta(score, "arranger") == "A"
