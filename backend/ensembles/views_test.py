import pytest
from unittest.mock import patch

from django.urls import reverse

from ensembles.models import ArrangementVersion, EnsembleUsership
from ensembles.factories import ArrangementFactory, ArrangementVersionFactory, EnsembleUsershipFactory


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


@pytest.mark.django_db
@patch("ensembles.tasks.export_arrangement_version.delay")
def test_trigger_audio_arrangement_version(mock_export, arrangement, client):
# def test_trigger_audio_arrangement_version(arrangement, client):
    version = ArrangementVersionFactory(arrangement=arrangement, is_latest=True)
    assert version.audio_state == ArrangementVersion.AudioStatus.NONE

    mock_export.return_value = {"status": "success"}

    url = reverse("ensembles:arrangementversion-trigger-audio-export", kwargs={"pk": version.pk})

    r = client.post(url)

    version.refresh_from_db()

    assert r.status_code == 202
    mock_export.assert_called_once_with(version.id, action="mp3")
    assert version.audio_state == ArrangementVersion.AudioStatus.PROCESSING


@pytest.mark.django_db
def test_remove_user_from_ensemble(ensemble, user, client):
    new_ship = EnsembleUsershipFactory(ensemble=ensemble)

    ensemble.owner = user
    ensemble.save()

    url = reverse("ensembles:ensemble-remove-user", kwargs={"slug": ensemble.slug})

    r = client.post(url, data={"user_id": new_ship.user.id}, content_type="application/json")
    
    assert r.status_code == 200, r.content
    assert not EnsembleUsership.objects.filter(user=new_ship.user).exists()
