import pytest
from unittest.mock import patch
from rest_framework.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.dateparse import parse_datetime

from ensembles.serializers import (
    ArrangementVersionSerializer,
    ArrangementSerializer,
    EnsembleSerializer,
    CreateArrangementVersionMsczSerializer,
    ArrangementVersionDownloadLinksSeiializer,
    DiffSerializer,
    ComputeDiffSerializer,
)
from ensembles.factories import (
    EnsembleFactory,
    ArrangementFactory,
    ArrangementVersionFactory,
    DiffFactory,
)


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


# -------------------------------------------------------------------
# Arrangement / Ensemble serializer tests
# -------------------------------------------------------------------


@pytest.mark.django_db
def test_arrangement_version_serializer(arrangement_versions):
    EXPECTED_FIELDS = ["id", "version_label", "timestamp", "is_latest"]

    v1, _ = arrangement_versions
    data = ArrangementVersionSerializer(v1).data

    assert len(data) == len(EXPECTED_FIELDS)

    EXPECTED_FIELDS.remove("timestamp")
    assert "timestamp" in data.keys()
    assert parse_datetime(data["timestamp"]) == v1.timestamp

    for field in EXPECTED_FIELDS:
        assert field in data
        assert data[field] == getattr(v1, field)


@pytest.mark.django_db
def test_arrangement_serializer_includes_latest_version(
    arrangement, arrangement_versions
):
    EXPECTED_FIELDS = [
        "id",
        "ensemble",
        "ensemble_name",
        "ensemble_slug",
        "title",
        "slug",
        "subtitle",
        "composer",
        "mvt_no",
        "style",
        "latest_version",
        "latest_version_num",
    ]
    _, latest = arrangement_versions
    data = ArrangementSerializer(arrangement).data

    assert len(data) == len(EXPECTED_FIELDS)

    # Don't want to auto-check serialized objects within serialized objects
    assert data["ensemble"] == arrangement.ensemble.id
    EXPECTED_FIELDS.remove("ensemble")
    assert data["latest_version"] == ArrangementVersionSerializer(latest).data
    EXPECTED_FIELDS.remove("latest_version")

    for field in EXPECTED_FIELDS:
        assert field in data
        assert data[field] == getattr(arrangement, field)


@pytest.mark.django_db
def test_ensemble_serializer_includes_arrangements(ensemble):
    data = EnsembleSerializer(ensemble).data
    assert data["name"] == ensemble.name
    assert isinstance(data["arrangements"], list)


# -------------------------------------------------------------------
# CreateArrangementVersionMsczSerializer tests
# -------------------------------------------------------------------


def test_create_arrangement_version_mscz_serializer_valid():
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": 1,
        "version_type": "minor",
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


def test_create_arrangement_version_mscz_serializer_invalid_version_type():
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": 1,
        "version_type": "invalid_type",
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert not serializer.is_valid()
    assert "Version type not one of" in str(serializer.errors)


# -------------------------------------------------------------------
# ComputeDiffSerializer validation tests
# -------------------------------------------------------------------


@pytest.mark.django_db
def test_compute_diff_serializer_requires_ids():
    serializer = ComputeDiffSerializer(data={})
    with pytest.raises(ValidationError):
        serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_compute_diff_serializer_invalid_diff_id():
    serializer = ComputeDiffSerializer(data={"diff_id": 999})
    with pytest.raises(ValidationError) as e:
        serializer.is_valid(raise_exception=True)
    assert "does not match any diffs" in str(e.value)


@pytest.mark.django_db
def test_compute_diff_serializer_invalid_version_ids(arrangement):
    serializer = ComputeDiffSerializer(data={"from_version_id": 1, "to_version_id": 2})
    with pytest.raises(ValidationError) as e:
        serializer.is_valid(raise_exception=True)
    assert "Invalid from_version_id" in str(e.value)


@pytest.mark.django_db
def test_compute_diff_serializer_different_arrangements(arrangement, ensemble):
    other_arr = ArrangementFactory(
        ensemble=ensemble,
        title="Other Piece",
        subtitle="",
        composer="Test",
        mvt_no="2",
        style="Jazz",
    )
    v1 = ArrangementVersionFactory(arrangement=arrangement, version_label="v1.0.0")
    v2 = ArrangementVersionFactory(arrangement=other_arr, version_label="v1.0.0")

    serializer = ComputeDiffSerializer(
        data={"from_version_id": v1.id, "to_version_id": v2.id}
    )
    with pytest.raises(ValidationError) as e:
        serializer.is_valid(raise_exception=True)
    assert "must be from the same arrangement" in str(e.value)


# -------------------------------------------------------------------
# ComputeDiffSerializer save() tests
# -------------------------------------------------------------------


@pytest.mark.django_db
@patch("ensembles.serializers.compute_diff.delay")
def test_compute_diff_serializer_creates_diff(mock_delay, arrangement_versions):
    v1, v2 = arrangement_versions
    data = {"from_version_id": v1.id, "to_version_id": v2.id}
    serializer = ComputeDiffSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    result = serializer.save()
    assert "id" in result
    assert result["status"] == "pending"
    mock_delay.assert_called_once()


@pytest.mark.django_db
@patch("ensembles.serializers.compute_diff.delay")
def test_compute_diff_serializer_existing_diff(mock_delay, diff):
    data = {"diff_id": diff.id}
    serializer = ComputeDiffSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    result = serializer.save()
    assert result["id"] == diff.id
    mock_delay.assert_not_called()
