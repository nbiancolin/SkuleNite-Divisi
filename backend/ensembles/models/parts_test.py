import pytest
import zipfile
import io
from unittest.mock import patch, MagicMock, mock_open
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from ensembles.models import ArrangementVersion, PartAsset, PartName
from ensembles.factories import (
    ArrangementVersionFactory,
    ArrangementFactory,
    EnsembleFactory,
    PartNameFactory,
    PartAssetFactory
)
from divisi.tasks.export import export_all_parts_with_tracking


@pytest.mark.django_db
def test_part_creation(arrangement_versions):
    """Test creating a Part record"""
    v1, v2 = arrangement_versions
    part = PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/violin.pdf",
        is_score=False,
    )

    assert part.name == "Violin"
    assert part.file_key == "test/violin.pdf"
    assert part.is_score is False
    assert part.arrangement_version == v1


@pytest.mark.django_db
def test_part_score_flag(arrangement_versions):
    """Test creating a score Part"""
    v1, _ = arrangement_versions
    score_part = PartAsset.objects.create(
        arrangement_version=v1, name="Score", file_key="test/score.pdf", is_score=True
    )

    assert score_part.is_score is True
    assert score_part.name == "Score"


@pytest.mark.django_db
def test_part_file_url(arrangement_versions):
    """Test Part file_url property"""
    v1, _ = arrangement_versions
    part = PartAsset.objects.create(
        arrangement_version=v1, name="Cello", file_key="test/cello.pdf", is_score=False
    )

    # file_url should return the storage URL
    url = part.file_url
    assert url is not None
    assert "cello.pdf" in url or "test/cello.pdf" in url


@pytest.mark.django_db
def test_part_ordering(arrangement_versions):
    """Test Part model ordering (score first, then alphabetically)"""
    v1, _ = arrangement_versions

    PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/violin.pdf",
        is_score=False,
    )
    PartAsset.objects.create(
        arrangement_version=v1, name="Score", file_key="test/score.pdf", is_score=True
    )
    PartAsset.objects.create(
        arrangement_version=v1, name="Cello", file_key="test/cello.pdf", is_score=False
    )

    parts = list(PartAsset.objects.filter(arrangement_version=v1))

    # Score should be first (is_score=True sorts before False)
    assert parts[0].is_score is True
    assert parts[0].name == "Score"

    # Then parts alphabetically
    assert parts[1].name == "Cello"
    assert parts[2].name == "Violin"


@pytest.mark.django_db
def test_part_deletion_with_version(arrangement_versions):
    """Test that Parts are deleted when ArrangementVersion is deleted"""
    v1, _ = arrangement_versions

    part1 = PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/violin.pdf",
        is_score=False,
    )
    part2 = PartAsset.objects.create(
        arrangement_version=v1, name="Cello", file_key="test/cello.pdf", is_score=False
    )

    assert PartAsset.objects.filter(arrangement_version=v1).count() == 2

    v1.delete()

    # Parts should be deleted via CASCADE
    assert PartAsset.objects.filter(id=part1.id).count() == 0
    assert PartAsset.objects.filter(id=part2.id).count() == 0


"""Tests for the export_all_parts_with_tracking function"""


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_creates_parts_successfully(mock_render, arrangement_versions):
    """Test that export creates Part records correctly"""
    v1, _ = arrangement_versions

    # Create a mock zip file with PDFs
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        # Add score PDF
        zip_file.writestr("Score.pdf", b"%PDF-1.4 fake score pdf content")
        # Add part PDFs
        zip_file.writestr("Violin.pdf", b"%PDF-1.4 fake violin pdf content")
        zip_file.writestr("Cello.pdf", b"%PDF-1.4 fake cello pdf content")

    mock_render.return_value = zip_buffer.getvalue()

    # Save a dummy input file to storage
    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    # Run export
    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    # Check results
    assert result["status"] == "success"
    assert result["parts_created"] == 3
    assert len(result["written"]) == 3

    # Check that Part records were created
    parts = PartAsset.objects.filter(arrangement_version=v1)
    assert parts.count() == 3

    # Check score part
    score_part = parts.filter(is_score=True).first()
    assert score_part is not None
    assert score_part.name == "Score"

    # Check other parts
    violin_part = parts.filter(name="Violin").first()
    assert violin_part is not None
    assert violin_part.is_score is False

    cello_part = parts.filter(name="Cello").first()
    assert cello_part is not None
    assert cello_part.is_score is False


@pytest.mark.django_db
def test_export_handles_missing_input_file(arrangement_versions):
    """Test export handles missing input file gracefully"""
    v1, _ = arrangement_versions

    # Don't create input file - ensure it doesn't exist
    input_key = v1.output_file_key
    if default_storage.exists(input_key):
        default_storage.delete(input_key)

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"

    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    assert result["status"] == "error"
    assert (
        "error" in result["details"].lower() or "download" in result["details"].lower()
    )


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_handles_invalid_zip(mock_render, arrangement_versions):
    """Test export handles invalid zip file"""
    v1, _ = arrangement_versions

    # Return invalid zip data
    mock_render.return_value = b"not a zip file"

    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    assert result["status"] == "error"
    assert "Invalid zip file" in result["details"]


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_handles_empty_zip(mock_render, arrangement_versions):
    """Test export handles empty zip file"""
    v1, _ = arrangement_versions

    # Create empty zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        pass  # Empty zip

    mock_render.return_value = zip_buffer.getvalue()

    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    assert result["status"] == "error"
    assert "no PDFs were extracted" in result["details"]


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_without_version_id(mock_render, arrangement_versions):
    """Test export works without creating Part records when version_id is None"""
    v1, _ = arrangement_versions

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("Score.pdf", b"%PDF-1.4 fake score pdf content")
        zip_file.writestr("Violin.pdf", b"%PDF-1.4 fake violin pdf content")

    mock_render.return_value = zip_buffer.getvalue()

    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=None
    )

    assert result["status"] == "success"
    assert result["parts_created"] == 0
    assert len(result["written"]) == 2

    # No Part records should be created
    assert PartAsset.objects.filter(arrangement_version=v1).count() == 0


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_handles_api_error(mock_render, arrangement_versions):
    """Test export handles MuseScore API errors"""
    v1, _ = arrangement_versions

    mock_render.side_effect = Exception("MuseScore API error")

    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    assert result["status"] == "error"
    assert "MuseScore API error" in result["details"]


@pytest.mark.django_db
def test_list_parts_endpoint(arrangement_versions, client):
    """Test listing parts for an arrangement version"""
    v1, _ = arrangement_versions

    # Create some parts
    PartAsset.objects.create(
        arrangement_version=v1, name="Score", file_key="test/score.pdf", is_score=True
    )
    PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/violin.pdf",
        is_score=False,
    )
    PartAsset.objects.create(
        arrangement_version=v1, name="Cello", file_key="test/cello.pdf", is_score=False
    )

    from django.urls import reverse

    url = reverse("ensembles:arrangementversion-list-parts", kwargs={"pk": v1.id})

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["version_id"] == v1.id
    assert data["count"] == 3
    assert len(data["parts"]) == 3

    # Check parts are ordered correctly (score first)
    assert data["parts"][0]["is_score"] is True
    assert data["parts"][0]["name"] == "Score"
    assert "download_url" in data["parts"][0]
    assert "file_url" in data["parts"][0]


@pytest.mark.django_db
def test_list_parts_empty(arrangement_versions, client):
    """Test listing parts when none exist"""
    v1, _ = arrangement_versions

    from django.urls import reverse

    url = reverse("ensembles:arrangementversion-list-parts", kwargs={"pk": v1.id})

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["parts"]) == 0


@pytest.mark.django_db
def test_list_parts_nonexistent_version(client):
    """Test listing parts for non-existent version"""
    from django.urls import reverse

    url = reverse("ensembles:arrangementversion-list-parts", kwargs={"pk": 99999})

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_download_part_endpoint(arrangement_versions, client):
    """Test downloading a specific part"""
    v1, _ = arrangement_versions

    # Create a part with a file in storage
    file_key = "test/violin.pdf"
    default_storage.save(file_key, ContentFile(b"%PDF-1.4 fake pdf"))

    part = PartAsset.objects.create(
        arrangement_version=v1, name="Violin", file_key=file_key, is_score=False
    )

    # Use the custom URL pattern
    url = f"/api/arrangementversions/{v1.id}/download_part/{part.id}/"

    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "file_url" in data
    assert "redirect" in data


@pytest.mark.django_db
def test_download_part_not_found(arrangement_versions, client):
    """Test downloading a part that doesn't exist"""
    v1, _ = arrangement_versions

    url = f"/api/arrangementversions/{v1.id}/download_part/99999/"

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_download_part_wrong_version(arrangement_versions, client):
    """Test downloading a part from wrong version"""
    v1, v2 = arrangement_versions

    part = PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/violin.pdf",
        is_score=False,
    )

    # Try to get part from v1 but using v2's ID
    url = f"/api/arrangementversions/{v2.id}/download_part/{part.id}/"

    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_download_part_missing_file(arrangement_versions, client):
    """Test downloading a part when file doesn't exist in storage"""
    v1, _ = arrangement_versions

    # Create part but don't save file to storage
    part = PartAsset.objects.create(
        arrangement_version=v1,
        name="Violin",
        file_key="test/nonexistent.pdf",
        is_score=False,
    )

    url = f"/api/arrangementversions/{v1.id}/download_part/{part.id}/"

    response = client.get(url)

    assert response.status_code == 404
    data = response.json()
    assert "not found in storage" in data["detail"].lower()


@pytest.mark.django_db
def test_merge_parts(ensemble, arrangement_versions):

    v1, v2 = arrangement_versions

    name1, name2 = PartNameFactory.create_batch(2, ensemble=ensemble)

    arr1_parts = [
        PartAssetFactory(arrangement_version=v1, part_name=name1),
        PartAssetFactory(arrangement_version=v1, part_name=name2),
    ]

    arr2_parts = [
        PartAssetFactory(arrangement_version=v2, part_name=name1),
        PartAssetFactory(arrangement_version=v2, part_name=name2),
    ]
    # WHEN
    part_name = PartName.merge_part_names(name1, name2, "New Merged Part")

    for part in arr1_parts + arr2_parts:
        part.refresh_from_db()
        assert part.part_name == part_name