"""Tests for MSCZ unpack/repack, styles, and part→MPOS wiring."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from mscz_formatter.mscz import (
    Style,
    format_mscz,
    get_score_attributes,
    list_excerpts,
    resolve_part_mpos,
    unpack_mscz_to_tempdir,
)
from mscz_formatter.mscz.styles import add_styles_to_score_and_parts

TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "test-data"
NEW_TEST_SCORE = TEST_DATA_DIR / "New-Test-Score.mscz"
SAMPLE_MPOS = TEST_DATA_DIR / "test.mpos"


def _write_mpos(path: Path, count: int = 8) -> None:
    elements = "\n".join(
        f'    <element id="{i}" x="0" y="0" sx="1000" sy="4000" page="0"></element>'
        for i in range(count)
    )
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f"<score><elements>\n{elements}\n  </elements></score>",
        encoding="utf-8",
    )


def test_unpack_lists_excerpts():
    with unpack_mscz_to_tempdir(str(NEW_TEST_SCORE), repack=False) as (
        work_dir,
        mscx_files,
    ):
        excerpts = list_excerpts(work_dir, mscx_files)
        assert len(excerpts) == 5
        assert excerpts[0].key == "0_Trumpet_in_Bb"
        assert excerpts[0].name == "Trumpet_in_Bb"
        assert excerpts[0].index == 0
        assert any("Excerpts" not in p for p in mscx_files)


def test_resolve_part_mpos_by_key_name_and_index(tmp_path):
    with unpack_mscz_to_tempdir(str(NEW_TEST_SCORE), repack=False) as (
        work_dir,
        mscx_files,
    ):
        excerpts = list_excerpts(work_dir, mscx_files)
        mpos_a = tmp_path / "a.mpos"
        mpos_b = tmp_path / "b.mpos"
        mpos_a.write_text("<score/>", encoding="utf-8")
        mpos_b.write_text("<score/>", encoding="utf-8")

        resolved = resolve_part_mpos(
            excerpts,
            {
                "0_Trumpet_in_Bb": str(mpos_a),
                "Trombone": str(mpos_b),
            },
        )
        assert set(resolved) == {"0_Trumpet_in_Bb", "1_Trombone"}

        by_index = resolve_part_mpos(excerpts, {"2": str(mpos_a)})
        assert "2_Piano" in by_index


def test_resolve_part_mpos_unknown_key_raises(tmp_path):
    with unpack_mscz_to_tempdir(str(NEW_TEST_SCORE), repack=False) as (
        work_dir,
        mscx_files,
    ):
        excerpts = list_excerpts(work_dir, mscx_files)
        missing = tmp_path / "x.mpos"
        missing.write_text("<score/>", encoding="utf-8")
        with pytest.raises(ValueError, match="No excerpt matched"):
            resolve_part_mpos(excerpts, {"NotAPart": str(missing)})


def test_add_styles_replaces_mss_files():
    with unpack_mscz_to_tempdir(str(NEW_TEST_SCORE), repack=False) as (work_dir, _):
        score_info = {"num_staves": 5}
        add_styles_to_score_and_parts(
            Style.BROADWAY,
            work_dir,
            score_info=score_info,
            staff_spacing_strategy="predict",
        )

        score_mss = Path(work_dir) / "score_style.mss"
        part_mss = (
            Path(work_dir) / "Excerpts" / "0_Trumpet_in_Bb" / "0_Trumpet_in_Bb.mss"
        )
        assert "DIVISI:staff_spacing" not in score_mss.read_text(encoding="utf-8")
        assert "<spatium>" in score_mss.read_text(encoding="utf-8")
        assert "<Style>" in part_mss.read_text(encoding="utf-8")


def test_get_score_attributes():
    info = get_score_attributes(str(NEW_TEST_SCORE))
    assert info["num_staves"] >= 1
    assert info["num_instruments"] >= 1


def test_format_mscz_requires_part_mpos(tmp_path):
    out = tmp_path / "out.mscz"
    with pytest.raises(ValueError, match="part_mpos is required"):
        format_mscz(str(NEW_TEST_SCORE), str(out), {})


def test_format_mscz_allows_empty_part_mpos_without_layout(tmp_path):
    out = tmp_path / "out.mscz"
    ok = format_mscz(
        str(NEW_TEST_SCORE),
        str(out),
        {},
        {"apply_part_layout": False, "apply_mss_style": True},
    )
    assert ok
    assert out.is_file()


def test_format_mscz_styles_only(tmp_path):
    """Apply styles for listed parts without running layout (avoids MPOS size mismatch)."""
    out = tmp_path / "styled.mscz"
    mpos = tmp_path / "trumpet.mpos"
    _write_mpos(mpos, 8)

    ok = format_mscz(
        str(NEW_TEST_SCORE),
        str(out),
        {"0_Trumpet_in_Bb": str(mpos)},
        {
            "selected_style": "jazz",
            "apply_part_layout": False,
            "apply_mss_style": True,
        },
    )
    assert ok
    assert out.is_file()

    with zipfile.ZipFile(out) as z:
        score_style = z.read("score_style.mss").decode("utf-8")
        assert "<Style>" in score_style
        assert "DIVISI:staff_spacing" not in score_style
