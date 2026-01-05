import pytest
import zipfile
import io
from unittest.mock import patch, MagicMock
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from ensembles.models import ArrangementVersion, Part, ExportFailureLog
from ensembles.factories import ArrangementVersionFactory, ArrangementFactory
from ensembles.tasks import export_arrangement_version



"""Tests for the export_arrangement_version task"""

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_creates_parts(self, mock_export, arrangement_versions):
    """Test that export_arrangement_version creates Part records"""
    v1, _ = arrangement_versions
    
    # Save input file
    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))
    
    # Mock the export function
    mock_export.return_value = {
        "status": "success",
        "written": ["file1.pdf", "file2.pdf"],
        "parts_created": 2
    }
    
    # Run the task
    result = export_arrangement_version(v1.id, action="score")
    
    # Verify
    assert result["status"] == "success"
    mock_export.assert_called_once()
    call_args = mock_export.call_args
    assert call_args[1]["arrangement_version_id"] == v1.id
    
    # Check version state
    v1.refresh_from_db()
    assert v1.error_on_export is False
    assert v1.is_processing is False

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_handles_error(self, mock_export, arrangement_versions):
    """Test that export_arrangement_version handles errors correctly"""
    v1, _ = arrangement_versions
    
    # Save input file
    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))
    
    # Mock the export function to return error
    mock_export.return_value = {
        "status": "error",
        "details": "Export failed"
    }
    
    # Run the task
    result = export_arrangement_version(v1.id, action="score")
    
    # Verify
    assert result["status"] == "error"
    
    # Check version state
    v1.refresh_from_db()
    assert v1.error_on_export is True
    assert v1.is_processing is False
    
    # Check that failure log was created
    assert ExportFailureLog.objects.filter(arrangement_version=v1).exists()

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_uses_processed_file(self, mock_export, arrangement_versions):
    """Test that export uses processed file when available"""
    v1, _ = arrangement_versions
    
    # Save processed file
    processed_key = v1.output_file_key
    default_storage.save(processed_key, ContentFile(b"processed mscz content"))
    
    mock_export.return_value = {"status": "success", "written": []}
    
    export_arrangement_version(v1.id, action="score")
    
    # Verify it was called with processed file key
    call_args = mock_export.call_args
    assert call_args[0][0] == processed_key

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_falls_back_to_raw_file(self, mock_export, arrangement_versions):
    """Test that export falls back to raw file if processed doesn't exist"""
    v1, _ = arrangement_versions
    
    # Save only raw file
    raw_key = v1.mscz_file_key
    default_storage.save(raw_key, ContentFile(b"raw mscz content"))
    
    mock_export.return_value = {"status": "success", "written": []}
    
    export_arrangement_version(v1.id, action="score")
    
    # Verify it was called with raw file key
    call_args = mock_export.call_args
    assert call_args[0][0] == raw_key

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_handles_missing_file(self, mock_export, arrangement_versions):
    """Test that export handles missing input file"""
    v1, _ = arrangement_versions
    
    # Don't save any files
    
    result = export_arrangement_version(v1.id, action="score")
    
    # Verify
    assert result["status"] == "error"
    assert "No input file found" in result["details"]
    
    # Check version state
    v1.refresh_from_db()
    assert v1.error_on_export is True
    assert v1.is_processing is False
    
    # Check that failure log was created
    assert ExportFailureLog.objects.filter(arrangement_version=v1).exists()

@pytest.mark.django_db
def test_export_nonexistent_version(self):
    """Test export with non-existent version ID"""
    result = export_arrangement_version(99999, action="score")
    
    assert result["status"] == "error"
    assert "not found" in result["details"].lower()

@pytest.mark.django_db
@patch('ensembles.tasks.export_all_parts_with_tracking')
def test_export_handles_exception(self, mock_export, arrangement_versions):
    """Test that export handles unexpected exceptions"""
    v1, _ = arrangement_versions
    
    input_key = v1.output_file_key
    default_storage.save(input_key, ContentFile(b"fake mscz content"))
    
    # Make export raise an exception
    mock_export.side_effect = Exception("Unexpected error")
    
    result = export_arrangement_version(v1.id, action="score")
    
    # Verify
    assert result["status"] == "error"
    
    # Check version state
    v1.refresh_from_db()
    assert v1.error_on_export is True
    assert v1.is_processing is False
    
    # Check that failure log was created
    assert ExportFailureLog.objects.filter(arrangement_version=v1).exists()

