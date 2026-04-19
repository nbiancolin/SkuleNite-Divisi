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
)
from ensembles.factories import (
    ArrangementFactory,
    ArrangementVersionFactory,
)


# -------------------------------------------------------------------
# Arrangement / Ensemble serializer tests
# -------------------------------------------------------------------


@pytest.mark.django_db
def test_arrangement_version_serializer(arrangement_versions):
    EXPECTED_FIELDS = ["id", "version_label", "timestamp", "is_latest", "audio_state"]

    v1, _ = arrangement_versions
    data = ArrangementVersionSerializer(v1).data

    assert len(data) == len(EXPECTED_FIELDS)

    EXPECTED_FIELDS.remove("timestamp")
    assert "timestamp" in data.keys()
    assert parse_datetime(data["timestamp"]) == v1.timestamp
    assert data["audio_state"] == "none"
    EXPECTED_FIELDS.remove("audio_state")

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

@pytest.mark.django_db
def test_create_arrangement_version_mscz_serializer_valid(arrangement):
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": arrangement.id,
        "version_type": "minor",
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

@pytest.mark.django_db
def test_create_arrangement_version_mscz_serializer_invalid_version_type(arrangement):
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": arrangement.id,
        "version_type": "invalid_type",
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert not serializer.is_valid()
    assert "Version type not one of" in str(serializer.errors)


@pytest.mark.django_db
def test_create_arrangement_version_mscz_serializer_formatting_steps_unknown_key(arrangement):
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": arrangement.id,
        "version_type": "minor",
        "formatting_steps": {"apply_mss_style": False, "not_a_real_step": True},
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert not serializer.is_valid()
    assert "Unknown formatting_steps keys" in str(serializer.errors)


@pytest.mark.django_db
def test_create_arrangement_version_mscz_serializer_formatting_steps_partial(arrangement):
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": arrangement.id,
        "version_type": "minor",
        "formatting_steps": {"apply_mss_style": False},
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["formatting_steps"]["apply_mss_style"] is False
    assert serializer.validated_data["formatting_steps"]["apply_score_metadata"] is True
    assert serializer.validated_data["formatting_steps"]["apply_scrub_existing_line_breaks"] is False


@pytest.mark.django_db
def test_create_arrangement_version_mscz_serializer_line_breaks_force_mm_rest_steps(arrangement):
    fake_file = SimpleUploadedFile("score.mscz", b"fakecontent")
    data = {
        "file": fake_file,
        "arrangement_id": arrangement.id,
        "version_type": "minor",
        "formatting_steps": {
            "apply_rehearsal_line_breaks": True,
            "apply_multimeasure_rest_prep": False,
            "apply_multimeasure_rest_cleanup": False,
        },
    }
    serializer = CreateArrangementVersionMsczSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["formatting_steps"]["apply_multimeasure_rest_prep"] is True
    assert serializer.validated_data["formatting_steps"]["apply_multimeasure_rest_cleanup"] is True
