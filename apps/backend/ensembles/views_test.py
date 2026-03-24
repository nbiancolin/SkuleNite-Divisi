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


@pytest.mark.django_db
def test_part_order_set_on_creation(ensemble):
    """Test that new PartName objects get order set automatically"""
    from ensembles.models import PartName
    
    # Create first part - should get order 0
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute")
    assert part1.order == 0
    
    # Create second part - should get order 1
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet")
    assert part2.order == 1
    
    # Create third part - should get order 2
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone")
    assert part3.order == 2


@pytest.mark.django_db
def test_part_order_preserved_when_existing(ensemble):
    """Test that existing PartName objects keep their order when updated"""
    from ensembles.models import PartName
    
    # Create part with explicit order
    part = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=5)
    assert part.order == 5
    
    # Update display name - order should remain
    part.display_name = "Flute I"
    part.save()
    part.refresh_from_db()
    assert part.order == 5


@pytest.mark.django_db
def test_update_part_order_as_admin(ensemble, user, client):
    """Test that admins can update part order"""
    from ensembles.models import PartName
    
    ensemble.owner = user
    ensemble.save()
    
    # Create parts
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone", order=2)
    
    url = reverse("ensembles:ensemble-update-part-order", kwargs={"slug": ensemble.slug})
    
    # Reorder: swap part1 and part2
    data = {
        "part_orders": [
            {"id": part1.id, "order": 1},
            {"id": part2.id, "order": 0},
            {"id": part3.id, "order": 2},
        ]
    }
    
    r = client.post(url, data=data, content_type="application/json")
    assert r.status_code == 200, r.content
    
    # Verify order was updated
    part1.refresh_from_db()
    part2.refresh_from_db()
    part3.refresh_from_db()
    
    assert part1.order == 1
    assert part2.order == 0
    assert part3.order == 2


@pytest.mark.django_db
def test_update_part_order_as_non_admin(ensemble, user, client):
    """Test that non-admins cannot update part order"""
    from ensembles.models import PartName, EnsembleUsership
    
    # Create another user who is not an admin
    from ensembles.factories import UserFactory
    non_admin = UserFactory()
    
    # Make them a member (not admin)
    EnsembleUsership.objects.create(ensemble=ensemble, user=non_admin)
    
    # Create parts
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    
    url = reverse("ensembles:ensemble-update-part-order", kwargs={"slug": ensemble.slug})
    
    data = {
        "part_orders": [
            {"id": part1.id, "order": 1},
            {"id": part2.id, "order": 0},
        ]
    }
    
    # Login as non-admin
    client.force_login(non_admin)
    r = client.post(url, data=data, content_type="application/json")
    
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()


@pytest.mark.django_db
def test_update_part_order_invalid_part_id(ensemble, user, client):
    """Test that updating order with invalid part ID fails"""
    from ensembles.models import PartName
    
    ensemble.owner = user
    ensemble.save()
    
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    
    url = reverse("ensembles:ensemble-update-part-order", kwargs={"slug": ensemble.slug})
    
    # Try to update with invalid part ID
    data = {
        "part_orders": [
            {"id": 99999, "order": 0},  # Invalid ID
        ]
    }
    
    r = client.post(url, data=data, content_type="application/json")
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


@pytest.mark.django_db
def test_update_part_order_wrong_ensemble(ensemble, user, client):
    """Test that updating order with part from different ensemble fails"""
    from ensembles.models import PartName
    from ensembles.factories import EnsembleFactory
    
    ensemble.owner = user
    ensemble.save()
    
    other_ensemble = EnsembleFactory()
    part1 = PartName.objects.create(ensemble=other_ensemble, display_name="Flute", order=0)
    
    url = reverse("ensembles:ensemble-update-part-order", kwargs={"slug": ensemble.slug})
    
    data = {
        "part_orders": [
            {"id": part1.id, "order": 0},  # Part from different ensemble
        ]
    }
    
    r = client.post(url, data=data, content_type="application/json")
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower() or "belong" in r.json()["detail"].lower()


@pytest.mark.django_db
def test_part_names_serialized_with_order(ensemble, user, client):
    """Test that part names are serialized with order and sorted correctly"""
    from ensembles.models import PartName
    
    ensemble.owner = user
    ensemble.save()
    
    # Create parts in reverse order
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone", order=2)
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    
    url = reverse("ensembles:ensemble-detail", kwargs={"slug": ensemble.slug})
    client.force_login(user)
    r = client.get(url)
    
    assert r.status_code == 200
    data = r.json()
    
    # Check that part_names are included and ordered correctly
    assert "part_names" in data
    part_names = data["part_names"]
    assert len(part_names) == 3
    
    # Should be ordered by order field
    assert part_names[0]["id"] == part1.id
    assert part_names[0]["order"] == 0
    assert part_names[1]["id"] == part2.id
    assert part_names[1]["order"] == 1
    assert part_names[2]["id"] == part3.id
    assert part_names[2]["order"] == 2


@pytest.mark.django_db
def test_part_names_with_null_order_sorted_last(ensemble, user, client):
    """Test that parts with null order are sorted last"""
    from ensembles.models import PartName
    
    ensemble.owner = user
    ensemble.save()
    
    # Create parts: some with order, some without
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    # Create part without order (simulating old data)
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone")
    part3.order = None
    part3.save()
    
    url = reverse("ensembles:ensemble-detail", kwargs={"slug": ensemble.slug})
    client.force_login(user)
    r = client.get(url)
    
    assert r.status_code == 200
    data = r.json()
    
    part_names = data["part_names"]
    # Parts with order should come first
    assert part_names[0]["id"] == part1.id
    assert part_names[1]["id"] == part2.id
    # Part with null order should come last
    assert part_names[2]["id"] == part3.id
    assert part_names[2]["order"] is None