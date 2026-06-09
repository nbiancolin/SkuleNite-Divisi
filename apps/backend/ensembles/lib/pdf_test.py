from io import BytesIO

import pytest
from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas

from ensembles.lib.fonts import IS_CI
from ensembles.lib.pdf import (
    _pages_before_content,
    count_pdf_pages,
    generate_full_part_book,
    merge_pdfs,
)


def _make_single_page_pdf(label: str = "page") -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesizes.LETTER)
    c.drawString(100, 700, label)
    c.save()
    buf.seek(0)
    return buf


def _make_toc_entry(title: str) -> dict:
    return {
        "show_number": "1",
        "title": title,
        "version_label": "v1.0.0",
        "page": -1,
    }


def test_pages_before_content_offsets():
    assert _pages_before_content("single_sided") == 2
    assert _pages_before_content("double_sided") == 4


def test_merge_pdfs_raw_has_no_blank_pages_between_content():
    pdf1 = _make_single_page_pdf("song1")
    pdf2 = _make_single_page_pdf("song2")
    result = merge_pdfs(
        cover_pdf=None,
        content_pdfs=[
            (_make_toc_entry("Song 1"), pdf1),
            (_make_toc_entry("Song 2"), pdf2),
        ],
        page_merge_strategy="raw",
    )
    assert count_pdf_pages(result["pdf"]) == 2
    assert result["toc_entries"][0]["page"] == 1
    assert result["toc_entries"][1]["page"] == 2


def test_merge_pdfs_optimize_does_not_pad_single_page_songs():
    pdf1 = _make_single_page_pdf("song1")
    pdf2 = _make_single_page_pdf("song2")
    result = merge_pdfs(
        cover_pdf=None,
        content_pdfs=[
            (_make_toc_entry("Song 1"), pdf1),
            (_make_toc_entry("Song 2"), pdf2),
        ],
        page_merge_strategy="optimize",
    )
    # Two 1-page songs: placement does not matter, so no page-turn padding
    assert count_pdf_pages(result["pdf"]) == 2


@pytest.mark.skipif(IS_CI, reason="WeasyPrint PDF smoke test skipped in CI")
def test_generate_full_part_book_single_sided_front_matter():
    from ensembles.lib.pdf import generate_cover_page

    cover_pdf = generate_cover_page(
        export_date="2026-01-06",
        part_name="Piano",
        show_title="Test Show",
    )
    content_pdf = _make_single_page_pdf("content")
    toc_kwargs = {
        "show_title": "Test Show",
        "show_subtitle": "",
        "export_date": "2026-01-06",
        "part_name": "Piano",
        "selected_style": "broadway",
    }
    result = generate_full_part_book(
        cover_pdf=cover_pdf,
        toc_kwargs=toc_kwargs,
        content_pdfs=[(_make_toc_entry("Song 1"), content_pdf)],
        layout="single_sided",
    )
    # cover (1) + toc (1) + content (1) = 3 pages, no blanks
    assert count_pdf_pages(result) == 3


@pytest.mark.skipif(IS_CI, reason="WeasyPrint PDF smoke test skipped in CI")
def test_generate_full_part_book_double_sided_front_matter():
    from ensembles.lib.pdf import generate_cover_page

    cover_pdf = generate_cover_page(
        export_date="2026-01-06",
        part_name="Piano",
        show_title="Test Show",
    )
    content_pdf = _make_single_page_pdf("content")
    toc_kwargs = {
        "show_title": "Test Show",
        "show_subtitle": "",
        "export_date": "2026-01-06",
        "part_name": "Piano",
        "selected_style": "broadway",
    }
    result = generate_full_part_book(
        cover_pdf=cover_pdf,
        toc_kwargs=toc_kwargs,
        content_pdfs=[(_make_toc_entry("Song 1"), content_pdf)],
        layout="double_sided",
    )
    # cover (1) + blank (1) + toc (1) + blank (1) + content (1) = 5 pages
    assert count_pdf_pages(result) == 5
