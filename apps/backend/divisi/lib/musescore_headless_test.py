import pytest
import zipfile
import io
from unittest.mock import patch, MagicMock, mock_open
import requests

from divisi.lib.musescore_headless import render_all_parts_pdf

"""Tests for the render_all_parts_pdf function"""

@pytest.mark.django_db
@patch('divisi.lib.musescore_headless.requests.post')
@patch('builtins.open', new_callable=mock_open, read_data=b"fake mscz content")
def test_render_all_parts_pdf_success(mock_file, mock_post):
    """Test successful call to render-all-parts-pdf endpoint"""
    # Create a mock zip file response
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr("Score.pdf", b"%PDF-1.4 fake score")
        zip_file.writestr("Violin.pdf", b"%PDF-1.4 fake violin")
    
    mock_response = MagicMock()
    mock_response.content = zip_buffer.getvalue()
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    # Call the function
    result = render_all_parts_pdf("/tmp/test.mscz")
    
    # Verify
    assert result == zip_buffer.getvalue()
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "render-all-parts-pdf" in call_args[0][0]
    assert call_args[1]["timeout"] == 300
    mock_file.assert_called_once_with("/tmp/test.mscz", "rb")

@pytest.mark.django_db
@patch('divisi.lib.musescore_headless.requests.post')
@patch('builtins.open', new_callable=mock_open, read_data=b"fake mscz content")
def test_render_all_parts_pdf_http_error(mock_file, mock_post):
    """Test handling of HTTP errors"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_post.return_value = mock_response
    
    with pytest.raises(requests.HTTPError):
        render_all_parts_pdf("/tmp/test.mscz")
    
    mock_file.assert_called_once_with("/tmp/test.mscz", "rb")

@pytest.mark.django_db
@patch('divisi.lib.musescore_headless.requests.post')
@patch('builtins.open', new_callable=mock_open, read_data=b"fake mscz content")
def test_render_all_parts_pdf_connection_error(mock_file, mock_post):
    """Test handling of connection errors"""
    mock_post.side_effect = requests.ConnectionError("Connection failed")
    
    with pytest.raises(requests.ConnectionError):
        render_all_parts_pdf("/tmp/test.mscz")
    
    mock_file.assert_called_once_with("/tmp/test.mscz", "rb")

@pytest.mark.django_db
@patch('divisi.lib.musescore_headless.requests.post')
@patch('builtins.open', new_callable=mock_open, read_data=b"fake mscz content")
def test_render_all_parts_pdf_timeout(mock_file, mock_post):
    """Test handling of timeout errors"""
    mock_post.side_effect = requests.Timeout("Request timed out")
    
    with pytest.raises(requests.Timeout):
        render_all_parts_pdf("/tmp/test.mscz")
    
    mock_file.assert_called_once_with("/tmp/test.mscz", "rb")

@pytest.mark.django_db
@patch('divisi.lib.musescore_headless.requests.post')
def test_render_all_parts_pdf_file_handling( mock_post):
    """Test that file is opened and sent correctly"""
    mock_response = MagicMock()
    mock_response.content = b"fake zip content"
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    with patch('builtins.open', mock_open(read_data=b"fake mscz content")) as mock_file:
        render_all_parts_pdf("/tmp/test.mscz")
        
        # Verify file was opened
        mock_file.assert_called_once_with("/tmp/test.mscz", "rb")
        
        # Verify POST was called with file
        call_args = mock_post.call_args
        assert "files" in call_args[1]
        assert "file" in call_args[1]["files"]

