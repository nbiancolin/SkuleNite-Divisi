import pytest

from ensembles.lib.pdf import generate_cover_page, generate_tacet_page


def test_generate_cover_page():
    # Uncomment this test to generate a sample cover page

    page = generate_cover_page(
        export_date="2026-01-06",
        part_name="Piano 1",
        show_title="Test Show",
        copyright="sample copyright test 123123123",
    )

    with open("sample-cover-page.pdf", mode="wb") as f:
        f.write(page.getbuffer())

def test_generate_tacet_page():
    #uncomment this test to generate a sample tacet page

    page = generate_tacet_page(
        show_title="Test Show",
        show_number="7",
        export_date="2026-01-06",
        song_title="My First Song",
        part_name="Piano 1"
    )

    with open("sample-tacet-page.pdf", mode="wb") as f:
        f.write(page.getbuffer())