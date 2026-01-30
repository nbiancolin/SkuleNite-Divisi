from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
from pypdf import PdfWriter, PdfReader

from ensembles.models.constants import STYLE_CHOICES

from typing import TypedDict


class TocEntry(TypedDict):
    """Data used to generate a table of contents"""

    show_number: str
    title: str
    version_label: str  # v1.0.0 or wtv
    page: int  # ie. the page number it starts on. Tbd if this is eeded


class EnsembleInfo(TypedDict):
    show_title: str
    show_number: str
    part_name: str
    selected_style: str


class MergedPdfResult(TypedDict):
    pdf: BytesIO
    toc_entries: list[TocEntry]


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

    font = "Inkpen2ScriptStd" if selected_style == "jazz" else "palatinolinotype_roman"

    c.setFont(font, 32)
    c.drawCentredString(width / 2, height / 2 + 60, show_title)

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


class PartBookInfo(TypedDict):
    show_title: str
    show_subtitle: str | None
    part_name: str
    export_date: str
    selected_style: str


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

    font = "Inkpen2ScriptStd" if selected_style == "jazz" else "palatinolinotype_roman"

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
        c.drawString(width * 1 / 5, y, lhs)
        c.drawRightString(width * 4 / 5, y, rhs)
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

    font = "Inkpen2ScriptStd" if selected_style == "jazz" else "palatinolinotype_roman"

    c.setFont(font, 32)
    # TODO[SC-279]: If title length is longer than a certain amount, bring it lower so it stays below the "show_title" text
    c.drawCentredString(width / 2, height - 80, song_title)

    if song_subtitle:
        c.setFont(font, 28)
        c.drawCentredString(width / 2, height - 120, song_subtitle)

    c.setFont(font, 32)  # not underlined
    text_width = stringWidth(show_number, font, 32)

    c.drawRightString(width - 60, height - 60, show_number)
    c.drawBoundary(
        None, (width - 60) - (text_width + 15), (height - 60) - 12, text_width + 30, 50
    )

    c.setFont(font, 12)  # make it underlined somehow?
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


def count_pdf_pages(pdf: BytesIO | str) -> int:
    reader = PdfReader(pdf)
    return len(reader.pages)


def add_blank_page(writer: PdfWriter):
    writer.add_blank_page(
        width=pagesizes.LETTER[0],
        height=pagesizes.LETTER[1],
    )


def overlay_page_numbers(
    *,
    writer: PdfWriter,
    start_page_number: int = 1,
    skip_page: int = 0,
    font_name: str = "palatinolinotype_roman",
    font_size: int = 10,
):
    """
    Overlay page numbers on every page in writer.
    """
    #TODO[SC-280]: This does a terrible job with page numbers. Ignoring it for now as i don't have time to fix it but eventually fix
    for i, page in enumerate(writer.pages):
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=pagesizes.LETTER)

        page_num = start_page_number + i
        c.setFont(font_name, font_size)
        if page_num > skip_page:
            c.drawCentredString(
                pagesizes.LETTER[0] / 2,
                pagesizes.LETTER[0] - 40,
                str(page_num),
            )

        c.save()
        packet.seek(0)

        overlay = PdfReader(packet).pages[0]
        page.merge_page(overlay)


def merge_pdfs(
    *,
    cover_pdf: BytesIO | None,
    content_pdfs: list[tuple[TocEntry, BytesIO | str]],
    # TODO[SC-281]: Allow setting which pdfs to start on a blank page
    start_on_odd_page: bool = True,
    overwrite_page_numbers: bool = False, #TODO[SC-280]: Fix this, its janky rn
    first_content_page_number: int = 1,
) -> MergedPdfResult:
    """
    Merge PDFs and compute TOC page numbers.

    content_pdfs:
        List of (toc_entry, pdf) where toc_entry.page will be filled in.
    """

    writer = PdfWriter()
    current_page = 0
    toc_entries: list[TocEntry] = []

    # Cover page
    if cover_pdf:
        cover_reader = PdfReader(cover_pdf)
        writer.append(cover_reader)
        current_page += len(cover_reader.pages)

    # Main content
    for entry, pdf in content_pdfs:
        reader = PdfReader(pdf)

        # Ensure odd-page start if requested
        if start_on_odd_page and current_page % 2 == 1:
            add_blank_page(writer)
            current_page += 1

        # Record TOC page (1-based, after cover)
        entry = entry.copy()
        entry["page"] = current_page + 1
        toc_entries.append(entry)

        writer.append(reader)
        current_page += len(reader.pages)

    # Page numbering
    if overwrite_page_numbers:
        overlay_page_numbers(
            writer=writer,
            start_page_number=first_content_page_number,
        )

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return {
        "pdf": output,
        "toc_entries": toc_entries,
    }


def generate_full_part_book(
    *,
    cover_pdf: BytesIO,
    toc_kwargs: dict,
    content_pdfs: list[tuple[TocEntry, BytesIO | str]],
) -> BytesIO:
    """
    Full two-pass generation:
    cover -> toc -> content
    """

    # Pass 1: merge content only (no cover) to get TOC page numbers and content PDF
    pass1 = merge_pdfs(
        cover_pdf=None,
        content_pdfs=content_pdfs,
        overwrite_page_numbers=False,
    )

    # TOC page numbers must account for: cover (1) + blank (1) + toc (1) + blank (1) = 4 pages before content
    pages_before_content = 4
    toc_entries_with_offset = [
        {**entry, "page": entry["page"] + pages_before_content}
        for entry in pass1["toc_entries"]
    ]

    # Generate TOC PDF
    toc_pdf = generate_table_of_contents(
        table_contents_data=toc_entries_with_offset,
        **toc_kwargs,
    )

    # Pass 2: final merge (cover already added here; pass1["pdf"] is content-only)
    writer = PdfWriter()
    writer.append(PdfReader(cover_pdf))
    add_blank_page(writer)
    writer.append(PdfReader(toc_pdf))
    add_blank_page(writer)
    writer.append(PdfReader(pass1["pdf"]))

    # overlay_page_numbers(writer=writer, start_page_number=5)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
