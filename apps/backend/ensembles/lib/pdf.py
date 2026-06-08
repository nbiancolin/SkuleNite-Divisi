from reportlab.lib import pagesizes
from reportlab.pdfgen import canvas
from io import BytesIO
from pypdf import PdfWriter, PdfReader

from ensembles.lib.part_book_pdf import render_part_book_html

from typing import TypedDict, Literal


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
    Generate a Cover page for a divisi app ensemble book (HTML template + WeasyPrint).
    """
    return render_part_book_html(
        "part_book/cover.html",
        selected_style=selected_style,
        export_date=export_date,
        part_name=part_name,
        show_title=show_title,
        show_subtitle=show_subtitle,
        copyright=copyright,
    )


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
    return render_part_book_html(
        "part_book/toc.html",
        selected_style=selected_style,
        show_title=show_title,
        show_subtitle=show_subtitle,
        part_name=part_name,
        export_date=export_date,
        entries=list(table_contents_data),
    )


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
    return render_part_book_html(
        "part_book/tacet.html",
        selected_style=selected_style,
        show_title=show_title,
        show_number=show_number,
        export_date=export_date,
        song_title=song_title,
        song_subtitle=song_subtitle,
        part_name=part_name,
    )


def generate_page_turn_page(
    part_name: str, show_title: str, export_date: str, show_number: str | None, **kwargs
) -> BytesIO:
    if not show_number:
        show_number = ""
    return render_part_book_html(
        "part_book/page_turn.html",
        part_name=part_name,
        show_title=show_title,
        show_number=show_number,
        export_date=export_date,
    )


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
    # TODO[SC-280]: This does a terrible job with page numbers. Ignoring it for now as i don't have time to fix it but eventually fix
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


def _should_add_blank_page(current_page_position: bool, num_pages: int) -> bool:
    """
    current_page_position:
    True: pdf will start on RHS (odd)
    False: pdf will start on LHS (even)

    return:
    True: insert a blank (V.S.) Page
    False: do not insert a blank page
    """

    match num_pages:
        case 1:
            # just append it, we dont really care
            return False
        case 2:
            # we could optimize this probably but who cares, ease of reading > saving a couple sheets of paper
            return current_page_position  # always start on LHS
        # case 4:
        #     return False # TODO: could try this
        case _:
            return not current_page_position  # Start on RHS


def merge_pdfs(
    *,
    cover_pdf: BytesIO | None,
    content_pdfs: list[tuple[TocEntry, BytesIO | str]],
    page_turn_page: BytesIO
    | None = None,  # If this is not passed in, generate one w/o any focused txt
    page_merge_strategy: Literal["optimize"]
    | Literal["odd"]
    | Literal["raw"] = "optimize",
    overwrite_page_numbers: bool = False,  # TODO[SC-280]: Fix this, its janky rn
    first_content_page_number: int = 1,
) -> MergedPdfResult:
    """
    Merge PDFs and compute TOC page numbers.

    page_merge_strategy:
    - `optimize`: use custom divisi logic to try and line up pages well
    - `odd`: Ensure that every song starts on an odd page
    - `raw`: Just append the pdfs and no blank pages

    content_pdfs:
        List of (toc_entry, pdf) where toc_entry.page will be filled in.
    """

    assert page_merge_strategy in ["optimize", "odd", "raw"], (
        f"Invalid page merge strategy: {page_merge_strategy}"
    )

    writer = PdfWriter()
    current_page = 0
    toc_entries: list[TocEntry] = []

    if not page_turn_page:
        page_turn_page = generate_page_turn_page(
            part_name="", show_title="", show_number="", export_date=""
        )

    # Cover page
    if cover_pdf:
        cover_reader = PdfReader(cover_pdf)
        writer.append(cover_reader)
        current_page += len(cover_reader.pages)

    # Main content
    for entry, pdf in content_pdfs:
        reader = PdfReader(pdf)
        num_pages = len(reader.pages)

        match page_merge_strategy:
            case "optimize":
                # curr page is odd = RHS
                if _should_add_blank_page(
                    current_page_position=((current_page + 1) % 2 == 1),
                    num_pages=num_pages,
                ):
                    writer.append(page_turn_page)
                    current_page += 1

            case "odd":
                if current_page % 2 == 1:
                    add_blank_page(writer)
                    current_page += 1
            case "raw":
                pass

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

    from ensembles.lib.pdf import generate_page_turn_page

    page_turn_kwargs = toc_kwargs | {
        "show_number": ""
    }  # TODO: Assess if we even need this..
    page_turn = generate_page_turn_page(**page_turn_kwargs)
    # Pass 1: merge content only (no cover) to get TOC page numbers and content PDF
    pass1 = merge_pdfs(
        cover_pdf=None,
        content_pdfs=content_pdfs,
        overwrite_page_numbers=False,
        page_turn_page=page_turn,
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
