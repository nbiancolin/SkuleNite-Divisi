"""
Render part-book front matter (cover, TOC, tacet) from HTML templates via WeasyPrint.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

from django.template.loader import render_to_string
from weasyprint import CSS, HTML

FONT_DIR = Path(os.environ.get("PART_BOOK_FONT_DIR", "/usr/share/fonts/truetype/custom"))

# Filenames from assets/fonts.zip (see ensembles/lib/fonts.py)
FONT_FILES = {
    "roman": "palatinolinotype_roman.ttf",
    "jazz": "Inkpen2ScriptStd.ttf",
}


def _font_file_uri(filename: str) -> str | None:
    path = FONT_DIR / filename
    if path.is_file():
        return path.resolve().as_uri()
    return None


def _font_context(selected_style: str) -> dict:
    style_class = "style-jazz" if selected_style == "jazz" else "style-broadway"
    return {
        "style_class": style_class,
        "font_roman_uri": _font_file_uri(FONT_FILES["roman"]),
        "font_jazz_uri": _font_file_uri(FONT_FILES["jazz"]),
    }


def render_part_book_html(template_name: str, *, selected_style: str = "broadway", **context) -> BytesIO:
    """
    Render a part-book HTML template to a single-page Letter PDF.
    """
    full_context = {**context, **_font_context(selected_style)}
    html_string = render_to_string(template_name, full_context)
    css_string = render_to_string("part_book/styles.css", full_context)

    buffer = BytesIO()
    HTML(string=html_string).write_pdf(
        buffer,
        stylesheets=[CSS(string=css_string)],
    )
    buffer.seek(0)
    return buffer
