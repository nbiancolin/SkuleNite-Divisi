import pytest

from rest_framework.test import APIClient

@pytest.fixture(scope="module")
def client():
    yield APIClient()


