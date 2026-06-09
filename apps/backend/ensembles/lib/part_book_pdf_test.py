import pytest
from django.template.loader import render_to_string

from ensembles.lib.fonts import IS_CI
from ensembles.lib.part_book_pdf import _font_context, render_part_book_html


@pytest.mark.django_db
def test_part_book_templates_render():
    context = _font_context("broadway")
    context.update(
        show_title="Test Show",
        part_name="Piano 1",
        export_date="2026-01-06",
        show_subtitle="",
        copyright="",
    )
    html = render_to_string("part_book/cover.html", context)
    assert "Test Show" in html
    assert "Piano 1" in html


@pytest.mark.skipif(IS_CI, reason="WeasyPrint PDF smoke test skipped in CI")
@pytest.mark.django_db
def test_render_part_book_cover_pdf():
    pdf = render_part_book_html(
        "part_book/cover.html",
        selected_style="broadway",
        export_date="2026-01-06",
        part_name="Piano 1",
        show_title="Test Show",
        show_subtitle="",
        copyright="",
    )
    assert pdf.getbuffer().nbytes > 500
