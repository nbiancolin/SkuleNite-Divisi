import pytest

from ensembles.factories import (
    EnsembleFactory,
    ArrangementFactory,
    ArrangementVersionFactory,
    DiffFactory,
)

from rest_framework.test import APIClient

@pytest.fixture(scope="module")
def client():
    yield APIClient()



@pytest.fixture
def ensemble(django_db_blocker):
    with django_db_blocker.unblock():
        ensemble = EnsembleFactory(name="Test Ensemble")

    yield ensemble


@pytest.fixture
def arrangement(ensemble, django_db_blocker):
    with django_db_blocker.unblock():
        arrangement = ArrangementFactory(
            ensemble=ensemble,
            title="Test Piece",
            subtitle="A piece for testing",
            composer="Test Composer",
            mvt_no="1",
            style="Classical",
        )
    yield arrangement


@pytest.fixture
def arrangement_versions(arrangement, django_db_blocker):
    with django_db_blocker.unblock():
        v1 = ArrangementVersionFactory(
            arrangement=arrangement, version_label="v1.0.0", is_latest=False
        )
        v2 = ArrangementVersionFactory(
            arrangement=arrangement, version_label="v1.1.0", is_latest=True
        )
    return v1, v2


@pytest.fixture
def diff(arrangement_versions, django_db_blocker):
    v1, v2 = arrangement_versions
    with django_db_blocker.unblock():
        diff = DiffFactory(
            from_version=v1, to_version=v2, file_name="comp-diff.pdf", status="pending"
        )

    yield diff