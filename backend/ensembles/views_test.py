import pytest
from unittest.mock import patch

from django.urls import reverse

from ensembles.factories import ArrangementFactory


@pytest.mark.django_db
def test_arrangements_view_lists_correct_order_numerically(ensemble, client):
    arr1 = ArrangementFactory(ensemble=ensemble, mvt_no="1")
    arr2 = ArrangementFactory(ensemble=ensemble, mvt_no="2")
    arr3 = ArrangementFactory(ensemble=ensemble, mvt_no="10")

    url = reverse("ensembles:ensemble-arrangements", args=[ensemble.slug])

    r = client.get(url)
    assert r.status_code == 200

    data = r.data
    assert data[0]["mvt_no"] == "1"
    assert data[1]["mvt_no"] == "2"
    assert data[2]["mvt_no"] == "10"

@pytest.mark.django_db
def test_arrangements_view_lists_correct_order_with_dashes(ensemble, client):
    arr1 = ArrangementFactory(ensemble=ensemble, mvt_no="1-1")
    arr2 = ArrangementFactory(ensemble=ensemble, mvt_no="2-1")
    arr3 = ArrangementFactory(ensemble=ensemble, mvt_no="1-2")

    url = reverse("ensembles:ensemble-arrangements", args=[ensemble.slug])

    r = client.get(url)
    assert r.status_code == 200

    data = r.data
    assert data[0]["mvt_no"] == "1-1"
    assert data[1]["mvt_no"] == "1-2"
    assert data[2]["mvt_no"] == "2-1"

@pytest.mark.django_db
def test_arrangements_view_lists_correct_order_with_ms(ensemble, client):
    arr1 = ArrangementFactory(ensemble=ensemble, mvt_no="1m1")
    arr2 = ArrangementFactory(ensemble=ensemble, mvt_no="2m1")
    arr3 = ArrangementFactory(ensemble=ensemble, mvt_no="1m2")

    url = reverse("ensembles:ensemble-arrangements", args=[ensemble.slug])

    r = client.get(url)
    assert r.status_code == 200

    data = r.data
    assert data[0]["mvt_no"] == "1m1"
    assert data[1]["mvt_no"] == "1m2"
    assert data[2]["mvt_no"] == "2m1"