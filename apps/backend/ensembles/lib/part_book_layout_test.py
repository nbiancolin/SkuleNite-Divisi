import pytest

from ensembles.factories import EnsembleFactory, PartNameFactory
from ensembles.lib.part_book_layout import resolve_part_book_layout


@pytest.mark.django_db
def test_resolve_part_book_layout_uses_default():
    ensemble = EnsembleFactory(default_part_book_layout="double_sided")
    part = PartNameFactory(ensemble=ensemble)
    assert resolve_part_book_layout(part) == "double_sided"


@pytest.mark.django_db
def test_resolve_part_book_layout_uses_override():
    ensemble = EnsembleFactory(default_part_book_layout="double_sided")
    part = PartNameFactory(
        ensemble=ensemble, part_book_layout_override="single_sided"
    )
    assert resolve_part_book_layout(part) == "single_sided"


@pytest.mark.django_db
def test_resolve_part_book_layout_one_off_takes_precedence():
    ensemble = EnsembleFactory(default_part_book_layout="double_sided")
    part = PartNameFactory(
        ensemble=ensemble, part_book_layout_override="single_sided"
    )
    assert resolve_part_book_layout(part, one_off_layout="double_sided") == "double_sided"
