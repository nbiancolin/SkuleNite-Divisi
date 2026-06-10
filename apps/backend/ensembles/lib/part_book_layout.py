from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ensembles.models.part import PartName


def resolve_part_book_layout(
    part_name: "PartName",
    *,
    one_off_layout: str | None = None,
) -> str:
    if one_off_layout:
        return one_off_layout
    return part_name.effective_part_book_layout()
