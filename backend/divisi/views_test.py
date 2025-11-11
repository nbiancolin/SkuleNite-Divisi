# TODO: Write E2E test here that ensures that one can upload a file, 
# and it will return a formatted file url (and that the file exoists) and the pdf file (and that the pdf file exists)


import pytest
from unittest.mock import patch

from rest_framework.test import APIClient
from django.urls import reverse

from divisi.models import UploadSession

@pytest.fixture(scope="module")
def client():
    yield APIClient()


def get_format_payload(session_id):
    return {
        "session_id": session_id, 
        "style": "broadway",
        "show_title": "My Show",
        "show_number": "1-1",
        "measures_per_line":
    }

@
def test_part_formatter_endpoint_works(client):

    session = UploadSession.objects.create(filename="Test File")

    url = reverse("divisi:format-mscz")

    client.post(url, get_format_payload(session.id), format="json")