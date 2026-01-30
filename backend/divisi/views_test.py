import pytest
from unittest.mock import patch

from django.urls import reverse

from divisi.models import UploadSession

def get_format_payload(session_id):
    return {
        "session_id": session_id, 
        "style": "broadway",
        "show_title": "My Show",
        "show_number": "1-1",
        "measures_per_line": 6,
    }


#can test formatting works
@pytest.mark.django_db
@patch("divisi.serializers.export_mscz_to_pdf")
@patch("divisi.serializers.format_upload_session")
def test_part_formatter_endpoint_works(mock_export, mock_format, client):
    mock_export.return_value = {"status": "success", "output": "sample output"}
    mock_format.return_value = {"status": "success", "output": "sample output"}

    session = UploadSession.objects.create(file_name="Test File")
    url = reverse("divisi:part-formatter-format-mscz")

    print(UploadSession.objects.count())

    r = client.post(url, get_format_payload(session.id), format="json")

    assert r.status_code == 200, r.content
    session.refresh_from_db()
    assert session.completed is True



#test it all e2e