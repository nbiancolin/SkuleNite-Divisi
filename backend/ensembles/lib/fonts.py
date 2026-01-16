# pdf/fonts.py
import os
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = "/usr/share/fonts/truetype/custom"
_FONTS_REGISTERED = False

"""
Fonts in assets/fonts.zip (as of Jan 15, 2026)
Inkpen2ScriptStd
palatinolinotype_bold
palatinolinotype_bolditalic
palatinolinotype_italic
palatinolinotype_roman

"""

def _font_name_from_filename(filename: str) -> str:
    """
    Convert a font filename into a safe ReportLab font name.
    """
    name, _ = os.path.splitext(filename)
    name = re.sub(r"[^A-Za-z0-9_-]", "", name)
    return f"{name}"


def register_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    for filename in os.listdir(FONT_DIR):
        if not filename.lower().endswith((".ttf", )): #TODO: otf
            continue

        path = os.path.join(FONT_DIR, filename)
        font_name = _font_name_from_filename(filename)

        if font_name in pdfmetrics.getRegisteredFontNames():
            continue

        pdfmetrics.registerFont(TTFont(font_name, path))

    _FONTS_REGISTERED = True
