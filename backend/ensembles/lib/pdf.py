from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
from pypdf import PdfWriter, PdfReader

from ensembles.models import STYLE_CHOICES

from typing import TypedDict


class TocEntry(TypedDict):
    """Data used to generate a table of contents"""
    show_number: str
    title: str
    version_label: str #v1.0.0 or wtv
    page: int #ie. the page number it starts on. Tbd if this is eeded

# Fns needed
# Merge N many pdfs together (option to ensure they all start on an odd page for dbl sided printing)
# option to overwrite page numbers

# create cover page
def generate_cover_page(
    *,
    export_date: str,
    part_name: str,
    show_title: str,
    show_subtitle: str = "",
    copyright: str = "",
    logo=None,
    selected_style: str = "broadway",
    title_font: str = "",  # for future, to allow for a custom font on the title
) -> BytesIO:
    """
    Generate a Cover page for a divisi app ensemble book

    :param export_date: the day the book was exported. Taken in as a string so the format can be customized
    :type export_date: str
    :param copyright: Copyright Text to display on the bottom
    :type copyright: str
    :param part_name: Part name of part
    :type part_name: str
    :param show_title: Ensemble/show title
    :type show_title: str
    :param show_subtitle: Ensemble/show subtitle
    :type show_subtitle: str
    :param logo: (not implementted) path to a logo to display on the front page
    :param selected_style: selected style. "jazz" if jazz, "broadway" if broadway.
    :type selected_style: str
    :return: PDF object in memory. Write out afterwards
    :rtype: BytesIO
    """

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=pagesizes.LETTER)
    width, height = pagesizes.LETTER

    font = "Inkpen2 Script Std" if selected_style == "jazz" else "Palatino Linotype"

    # debug
    font = "Helvetica"

    c.setFont(font, 32)
    c.drawCentredString(width / 2, height / 2 + 40, show_title)

    if show_subtitle:
        c.setFont(font, 16)
        c.drawCentredString(width / 2, height / 2, show_subtitle)
        c.setFont(font, 14)
        c.drawCentredString(width / 2, height / 2 - 40, f"Rev: {export_date}")

    else:
        c.setFont(font, 14)
        c.drawCentredString(width / 2, height / 2, f"Rev: {export_date}")

    c.setFont(font, 20)
    c.drawCentredString(width / 2, height / 2 + 80, part_name)

    if copyright:
        c.setFont(font, 12)
        c.drawCentredString(width / 2, 80, copyright)

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


def generate_table_of_contents(
    *,
    show_title: str,
    show_subtitle: str = "",
    part_name: str,
    export_date: str,
    table_contents_data: list[TocEntry],  # (title, version label, page #)
    selected_style: str = "broadway",
) -> BytesIO:

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=pagesizes.LETTER)
    width, height = pagesizes.LETTER

    font = "Inkpen2 Script Std" if selected_style == "jazz" else "Palatino Linotype"

    # debug
    font = "Helvetica"

    c.setFont(font, 32)
    c.drawCentredString(width / 2, height - 80, show_title)
    if show_subtitle:
        c.setFont(font, 28)
        c.drawCentredString(width / 2, height - 120, show_subtitle)

    c.setFont(font, 16)
    c.drawString(60, height - 60, part_name)


    y = height - 160

    c.setFont(font, 12)
    while y > 160 and len(table_contents_data) > 0:
        entry = table_contents_data.pop()
        # lhs = f"<b>{entry['show_number']}: {entry['title']}</b> <i>({entry['version_label']})</i>"
        lhs = f"{entry['show_number']}: {entry['title']} ({entry['version_label']})"
        rhs = str(entry["page"])
        c.drawString(width * 1/5, y, lhs)
        c.drawRightString(width * 4/5, y, rhs)
        y += 20


    c.setFont(font, 12)
    c.drawCentredString(width / 2, 80, f"Rev. {export_date}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer



def generate_tacet_page(
    *,
    show_title: str,
    show_number: str,
    export_date: str,
    song_title: str,
    song_subtitle: str = "",
    part_name: str,
    selected_style: str = "broadway",
) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=pagesizes.LETTER)
    width, height = pagesizes.LETTER

    font = "Inkpen2 Script Std" if selected_style == "jazz" else "Palatino Linotype"

    # debug
    font = "Helvetica"

    c.setFont(font, 32)
    #TODO: If title length is longer than a certain amount, bring it lower so it stays below the "show_title" text
    c.drawCentredString(width / 2, height - 80, song_title)

    if song_subtitle:
        c.setFont(font, 28)
        c.drawCentredString(width / 2, height - 120, song_subtitle)


    c.setFont(font, 32)  # not underlined
    text_width = stringWidth(show_number, font, 32)

    c.drawRightString(width - 60, height - 60, show_number)
    c.drawBoundary(None, (width - 60) - (text_width + 15), (height - 60) -12, text_width + 30, 50)

    c.setFont(font, 16)  # make it underlined somehow?
    c.drawRightString((width - 60) - (text_width + 15) - 10, height - 60, show_title)

    c.drawString(60, height - 60, part_name)


    c.setFont(font, 32)
    c.drawCentredString(width / 2, height / 2 + 40, "TACET")

    c.setFont(font, 12)
    c.drawCentredString(width / 2, 80, f"Rev. {export_date}")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


def merge_pdfs(title_pdf: BytesIO, pdf_files: list[str]) -> BytesIO:
    writer = PdfWriter()

    # n.b. is this gonna error out bc not enough memory if we have a bunch of pdfs?
    # Mbe add a sanity chck layer that only does these in a few small increments

    #Or, if there are too may bytes, generate multiple smaller pdfs so as to not overload the machine (user then prints them 1 at a time)
    #Limit to 50 pages bc that is the ECF limit?

    # Add title page
    writer.append(PdfReader(title_pdf))

    # Add uploaded PDFs
    for pdf in pdf_files:
        writer.append(PdfReader(pdf))

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
