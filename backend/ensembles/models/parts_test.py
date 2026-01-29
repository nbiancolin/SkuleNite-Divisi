import pytest
import zipfile
import io
from unittest.mock import patch, MagicMock
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.urls import reverse

from ensembles.models import ArrangementVersion, PartAsset, PartName
from ensembles.models import PartNameAlias
from ensembles.factories import (
    ArrangementVersionFactory,
    ArrangementFactory,
    EnsembleFactory,
    PartNameFactory,
    PartAssetFactory,
    EnsembleUsershipFactory,
    UserFactory,
)
from ensembles.tasks.export import prep_and_export_mscz
from divisi.tasks.export import export_all_parts_with_tracking


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
    violin_name = PartName.objects.get(ensemble=v1.ensemble, display_name="Violin")
    violin_part = parts.filter(part_name=violin_name).first()
    assert violin_part is not None
    assert violin_part.is_score is False

    cello_name = PartName.objects.get(ensemble=v1.ensemble, display_name="Cello")
    cello_part = parts.filter(part_name=cello_name).first()
    assert cello_part is not None
    assert cello_part.is_score is False


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_export_respects_part_name_aliases(mock_render, arrangement_versions):
    v1, _ = arrangement_versions

    # Canonical name that the user wants (already exists in the ensemble)
    canonical = PartName.objects.create(ensemble=v1.ensemble, display_name="Flute 1")

    # Persisted alias from raw MuseScore name -> canonical (as created by a merge)
    PartNameAlias.objects.create(
        ensemble=v1.ensemble,
        arrangement=v1.arrangement,
        canonical_part_name=canonical,
        alias="Flute I",
    )

    # Create a mock zip file with PDFs containing the "raw" alias name
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("Score.pdf", b"%PDF-1.4 fake score pdf content")
        zip_file.writestr("Flute I.pdf", b"%PDF-1.4 fake flute pdf content")

    mock_render.return_value = zip_buffer.getvalue()

    # Save a dummy input file to storage
    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))

    output_prefix = f"ensembles/{v1.arrangement.ensemble.slug}/{v1.arrangement.slug}/{v1.version_label}/processed/"
    result = export_all_parts_with_tracking(
        input_key, output_prefix, arrangement_version_id=v1.id
    )

    assert result["status"] == "success"

    # Ensure no new PartName was created for the alias label.
    assert PartName.objects.filter(ensemble=v1.ensemble, display_name__iexact="Flute I").count() == 0

    # The created PartAsset should point at the canonical PartName.
    part_assets = PartAsset.objects.filter(arrangement_version=v1, is_score=False)
    assert part_assets.count() == 1
    assert part_assets.first().part_name_id == canonical.id


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
    PartAssetFactory(arrangement_version=v1, is_score=True)
    PartAssetFactory.create_batch(2, arrangement_version=v1, is_score=False)

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

    part = PartAssetFactory(
        arrangement_version=v1, file_key=file_key, is_score=False
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

    part = PartAssetFactory(
        arrangement_version=v1,
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
    part = PartAssetFactory(
        arrangement_version=v1,
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
    # WHEN / THEN: merging should fail because it would create multiple
    # PartAsset objects for the same arrangement_version under the merged name.
    with pytest.raises(ValidationError):
        PartName.merge_part_names(name1, name2, "New Merged Part")


@pytest.mark.django_db
def test_merge_persists_alias_for_future_uploads():
    ensemble = EnsembleFactory()
    v1 = ArrangementVersionFactory(arrangement__ensemble=ensemble)
    v2 = ArrangementVersionFactory(arrangement__ensemble=ensemble)  # different arrangement
    arrangement_a = v1.arrangement
    arrangement_b = v2.arrangement

    canonical = PartNameFactory(ensemble=ensemble, display_name="Flute 1")
    to_merge = PartNameFactory(ensemble=ensemble, display_name="Flute I")

    # No overlap: target (canonical) on v1, merge_from (to_merge) on v2.
    PartAssetFactory(arrangement_version=v1, part_name=canonical)
    PartAssetFactory(arrangement_version=v2, part_name=to_merge)

    merged = PartName.merge_part_names(canonical, to_merge, new_displayname="Flute")

    # Alias for the merged-away name exists for the arrangement that had merge_from (B).
    assert PartNameAlias.objects.filter(
        ensemble=ensemble,
        arrangement=arrangement_b,
        alias_normalized=PartNameAlias.normalize("Flute I"),
        canonical_part_name=merged,
    ).exists()

    # Old canonical name is an alias for the arrangement that had target (A).
    assert PartNameAlias.objects.filter(
        ensemble=ensemble,
        arrangement=arrangement_a,
        alias_normalized=PartNameAlias.normalize("Flute 1"),
        canonical_part_name=merged,
    ).exists()

    # Resolving for arrangement B (which had "Flute I") returns the canonical part name.
    resolved = PartName.resolve_for_arrangement(
        ensemble=ensemble, arrangement=arrangement_b, raw_display_name="Flute I"
    )
    assert resolved.id == merged.id
    assert PartName.objects.filter(ensemble=ensemble, display_name__iexact="Flute I").count() == 0


@pytest.mark.django_db
@patch("divisi.tasks.export.render_all_parts_pdf")
def test_merge_and_reupload_uses_alias(mock_render):
    """
    Integration test for the full user flow:
    1. Upload arrangement A with part "Flute I"
    2. Upload arrangement B with part "Flute 1"
    3. Merge "Flute I" and "Flute 1" into canonical "Flute"
    4. Upload arrangement A again with "Flute I" in the zip
    5. Verify the new version uses canonical "Flute" PartName (not creates new "Flute I")
    """
    ensemble = EnsembleFactory()
    
    # Step 1: Upload arrangement A with "Flute I"
    arrangement_a = ArrangementFactory(ensemble=ensemble, title="Arrangement A")
    version_a1 = ArrangementVersionFactory(
        arrangement=arrangement_a,
        version_label="1.0.0",
        is_latest=True,
    )
    
    zip_a1 = io.BytesIO()
    with zipfile.ZipFile(zip_a1, "w") as z:
        z.writestr("Score.pdf", b"%PDF-1.4 score")
        z.writestr("Flute I.pdf", b"%PDF-1.4 flute i part")
    
    mock_render.return_value = zip_a1.getvalue()
    input_key_a1 = version_a1.output_file_key
    default_storage.save(input_key_a1, ContentFile(b"fake mscz"))
    
    output_prefix_a1 = f"ensembles/{ensemble.slug}/{arrangement_a.slug}/{version_a1.version_label}/processed/"
    result_a1 = export_all_parts_with_tracking(
        input_key_a1, output_prefix_a1, arrangement_version_id=version_a1.id
    )
    assert result_a1["status"] == "success"
    
    # Verify A1 has "Flute I" PartName
    part_name_flute_i = PartName.objects.get(ensemble=ensemble, display_name="Flute I")
    part_asset_a1 = PartAsset.objects.get(
        arrangement_version=version_a1,
        part_name=part_name_flute_i,
        is_score=False,
    )
    assert part_asset_a1 is not None
    
    # Step 2: Upload arrangement B with "Flute 1"
    arrangement_b = ArrangementFactory(ensemble=ensemble, title="Arrangement B")
    version_b1 = ArrangementVersionFactory(
        arrangement=arrangement_b,
        version_label="1.0.0",
        is_latest=True,
    )
    
    zip_b1 = io.BytesIO()
    with zipfile.ZipFile(zip_b1, "w") as z:
        z.writestr("Score.pdf", b"%PDF-1.4 score")
        z.writestr("Flute 1.pdf", b"%PDF-1.4 flute 1 part")
    
    mock_render.return_value = zip_b1.getvalue()
    input_key_b1 = version_b1.output_file_key
    default_storage.save(input_key_b1, ContentFile(b"fake mscz"))
    
    output_prefix_b1 = f"ensembles/{ensemble.slug}/{arrangement_b.slug}/{version_b1.version_label}/processed/"
    result_b1 = export_all_parts_with_tracking(
        input_key_b1, output_prefix_b1, arrangement_version_id=version_b1.id
    )
    assert result_b1["status"] == "success"
    
    # Verify B1 has "Flute 1" PartName
    part_name_flute_1 = PartName.objects.get(ensemble=ensemble, display_name="Flute 1")
    part_asset_b1 = PartAsset.objects.get(
        arrangement_version=version_b1,
        part_name=part_name_flute_1,
        is_score=False,
    )
    assert part_asset_b1 is not None
    
    # Step 3: Merge "Flute I" and "Flute 1" into canonical "Flute"
    # (merge_from will be the one with fewer assets, or first if equal)

    merged_part_name = PartName.merge_part_names(
        part_name_flute_i, part_name_flute_1, new_displayname="Flute"
    )
    
    # Verify merge created the canonical PartName
    assert merged_part_name.display_name == "Flute"
    assert PartName.objects.filter(ensemble=ensemble, display_name="Flute").count() == 1
    
    # Verify alias was created for arrangement A (which had "Flute I")
    alias_for_a = PartNameAlias.objects.filter(
        ensemble=ensemble,
        arrangement=arrangement_a,
        alias_normalized=PartNameAlias.normalize("Flute I"),
        canonical_part_name=merged_part_name,
    ).first()
    assert alias_for_a is not None, "Alias for arrangement A should exist after merge"
    
    # Step 4: Upload arrangement A again (version 2) with "Flute I" in the zip
    version_a2 = ArrangementVersionFactory(
        arrangement=arrangement_a,
        version_label="1.1.0",
        is_latest=True,
    )
    # Mark old version as not latest
    version_a1.is_latest = False
    version_a1.save()
    
    zip_a2 = io.BytesIO()
    with zipfile.ZipFile(zip_a2, "w") as z:
        z.writestr("Score.pdf", b"%PDF-1.4 score v2")
        z.writestr("Flute I.pdf", b"%PDF-1.4 flute i part")  # Same raw name as A1 so alias is used
    
    mock_render.return_value = zip_a2.getvalue()
    input_key_a2 = version_a2.output_file_key
    default_storage.save(input_key_a2, ContentFile(b"fake mscz v2"))
    
    output_prefix_a2 = f"ensembles/{ensemble.slug}/{arrangement_a.slug}/{version_a2.version_label}/processed/"
    result_a2 = export_all_parts_with_tracking(
        input_key_a2, output_prefix_a2, arrangement_version_id=version_a2.id
    )
    assert result_a2["status"] == "success"
    
    # Step 5: Verify the new version uses canonical "Flute" PartName (NOT creates new "Flute I")
    # Check that no new "Flute I" PartName was created
    assert PartName.objects.filter(ensemble=ensemble, display_name__iexact="Flute I").count() == 0, \
        "Should NOT create a new 'Flute I' PartName after merge"
    
    # Check that the PartAsset for A2 points to the canonical "Flute" PartName
    part_asset_a2 = PartAsset.objects.get(
        arrangement_version=version_a2,
        is_score=False,
    )
    assert part_asset_a2.part_name_id == merged_part_name.id, \
        f"PartAsset for A2 should point to canonical 'Flute' (id={merged_part_name.id}), " \
        f"but points to '{part_asset_a2.part_name.display_name}' (id={part_asset_a2.part_name_id})"
    assert part_asset_a2.part_name.display_name == "Flute", \
        "PartAsset for A2 should use canonical 'Flute' PartName"
    
    # Verify there's still only one "Flute" PartName in the ensemble
    assert PartName.objects.filter(ensemble=ensemble, display_name="Flute").count() == 1, \
        "Should only have one canonical 'Flute' PartName"