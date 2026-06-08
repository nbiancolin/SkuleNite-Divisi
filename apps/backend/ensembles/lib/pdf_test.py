# Part-book cover / TOC / tacet pages are rendered from HTML templates under
# ensembles/templates/part_book/ (styles in styles.css). Uncomment tests below
# to write sample PDFs locally (requires WeasyPrint system libs + fonts).

# @pytest.fixture(autouse=True)
# def font_setup():
#     register_fonts()


# def test_generate_page_turn_page():
#     from ensembles.lib.pdf import generate_page_turn_page
#     page = generate_page_turn_page(
#         export_date="2026-01-06",
#         part_name="Piano 1",
#         show_title="Test Show",
#         show_number="",
#         copyright="sample copyright test 123123123",
#     )

#     with open("sample-page-turn-page.pdf", mode="wb") as f:
#         f.write(page.getbuffer())

# def test_generate_cover_page():
#     # Uncomment this test to generate a sample cover page

#     page = generate_cover_page(
#         export_date="2026-01-06",
#         part_name="Piano 1",
#         show_title="Test Show",
#         copyright="sample copyright test 123123123",
#     )

#     with open("sample-cover-page.pdf", mode="wb") as f:
#         f.write(page.getbuffer())

# def test_generate_tacet_page():
#     #uncomment this test to generate a sample tacet page

#     page = generate_tacet_page(
#         show_title="Test Show",
#         show_number="7",
#         export_date="2026-01-06",
#         song_title="My First Song",
#         part_name="Piano 1"
#     )

#     with open("sample-tacet-page.pdf", mode="wb") as f:
#         f.write(page.getbuffer())


# def test_generate_toc_page():
#     #uncomment this test to generate a sample table of contents page
#     toc_data: list[TocEntry] = [
#         {
#             "show_number": "1",
#             "page": 1,
#             "title": "My First Song",
#             "version_label": "v1.0.0"
#         },
#         {
#             "show_number": "2-1",
#             "page": 2,
#             "title": "My Second Song",
#             "version_label": "v1.2.1"
#         }
#     ]

#     page = generate_table_of_contents(
#         show_title="Test Show",
#         export_date="2026-01-06",
#         table_contents_data=toc_data,
#         part_name="Piano 1"
#     )

#     with open("sample-toc-page.pdf", mode="wb") as f:
#         f.write(page.getbuffer())
