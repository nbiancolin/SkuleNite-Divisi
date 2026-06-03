import pytest
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ensembles.models import ArrangementVersion, Commit, EnsembleUsership, UserScoreVersion
from ensembles.factories import (
    ArrangementFactory,
    ArrangementVersionFactory,
    EnsembleUsershipFactory,
    UserFactory,
)
from musescore_score_diff.merge import MergeConflictException


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.save")
def test_upload_new_commit_sets_created_by_on_second_upload(mock_save, arrangement, user, client):
    """Follow-up commits must record the authenticated user as created_by (regression)."""
    url = reverse("ensembles:arrangement-upload-new-commit", kwargs={"slug": arrangement.slug})
    r1 = client.post(
        url,
        data={
            "file": SimpleUploadedFile("first.mscz", b"x", content_type="application/octet-stream"),
            "message": "first",
        },
        format="multipart",
    )
    assert r1.status_code == 200, r1.content
    r2 = client.post(
        url,
        data={
            "file": SimpleUploadedFile("second.mscz", b"y", content_type="application/octet-stream"),
            "message": "second",
        },
        format="multipart",
    )
    assert r2.status_code == 200, r2.content
    commits = list(Commit.objects.filter(arrangement=arrangement).order_by("id"))
    assert len(commits) == 2
    assert commits[0].created_by_id == user.id
    assert commits[1].created_by_id == user.id
    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == commits[1].id


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.save")
@patch("ensembles.views.arrangement.default_storage.exists", return_value=True)
@patch("ensembles.views.arrangement.default_storage.open")
def test_download_latest_commit_mscz_sets_user_score_version(
    mock_open, mock_exists, mock_save, arrangement, user, client
):
    upload_url = reverse(
        "ensembles:arrangement-by-id-upload-new-commit", kwargs={"id": arrangement.id}
    )
    client.post(
        upload_url,
        data={
            "file": SimpleUploadedFile("score.mscz", b"x", content_type="application/octet-stream"),
        },
        format="multipart",
    )
    commit = Commit.latest_for_arrangement(arrangement)
    UserScoreVersion.objects.filter(user=user, arrangement=arrangement).delete()

    download_url = reverse(
        "ensembles:arrangement-by-id-download-latest-commit-mscz",
        kwargs={"id": arrangement.id},
    )
    mock_open.return_value = BytesIO(b"x")

    r = client.get(download_url)
    assert r.status_code == 200, r.content

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == commit.id


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.save")
def test_check_score_version_ok_when_user_has_latest(mock_save, arrangement, user, client):
    upload_url = reverse(
        "ensembles:arrangement-by-id-upload-new-commit", kwargs={"id": arrangement.id}
    )
    client.post(
        upload_url,
        data={
            "file": SimpleUploadedFile("score.mscz", b"x", content_type="application/octet-stream"),
        },
        format="multipart",
    )

    check_url = reverse(
        "ensembles:arrangement-by-id-check-score-version", kwargs={"id": arrangement.id}
    )
    r = client.get(check_url)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.save")
def test_check_score_version_error_when_never_downloaded(mock_save, arrangement, user, client):
    upload_url = reverse(
        "ensembles:arrangement-upload-new-commit", kwargs={"slug": arrangement.slug}
    )
    client.post(
        upload_url,
        data={
            "file": SimpleUploadedFile("score.mscz", b"x", content_type="application/octet-stream"),
        },
        format="multipart",
    )
    UserScoreVersion.objects.filter(user=user, arrangement=arrangement).delete()

    check_url = reverse(
        "ensembles:arrangement-by-id-check-score-version", kwargs={"id": arrangement.id}
    )
    r = client.get(check_url)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "error"
    assert data["user_download_commit"] is None


def _post_commit(client, arrangement, name: str, b: bytes = b"x", *, force: bool = False):
    upload_url = reverse(
        "ensembles:arrangement-by-id-upload-new-commit", kwargs={"id": arrangement.id}
    )
    data = {
        "file": SimpleUploadedFile(name, b, content_type="application/octet-stream"),
    }
    if force:
        data["force"] = True
    return client.post(
        upload_url,
        data=data,
        format="multipart",
    )


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.open")
@patch("ensembles.serializers.default_storage.save")
@patch("musescore_score_diff.merge.three_way_merge_mscz")
def test_upload_stale_merge_commit_does_not_update_user_score_version(
    mock_merge, mock_save, mock_open, mock_exists, arrangement, ensemble, user, client
):
    """Auto-merge tip is a merge commit; uploader's USV stays at their last-known commit."""
    mock_open.side_effect = lambda *_a, **_k: BytesIO(b"x")

    def write_merged_output(_base, _head, _user, output):
        with open(output, "wb") as out:
            out.write(b"merged")

    mock_merge.side_effect = write_merged_output

    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    base_commit = Commit.latest_for_arrangement(arrangement)

    other_user = UserFactory()
    EnsembleUsershipFactory(ensemble=ensemble, user=other_user)
    other_client = client.__class__()
    other_client.force_authenticate(user=other_user)
    assert _post_commit(other_client, arrangement, "head.mscz", b"y").status_code == 200

    usv_before = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv_before.commit_id == base_commit.id

    r = _post_commit(client, arrangement, "user.mscz", b"z")
    assert r.status_code == 200, r.content

    usv_after = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv_after.commit_id == base_commit.id

    tip = Commit.latest_for_arrangement(arrangement)
    assert tip.is_merge_commit is True
    assert tip.is_merge_conflict is False


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.open")
@patch("ensembles.serializers.default_storage.save")
@patch("musescore_score_diff.merge.three_way_merge_mscz")
def test_upload_stale_merge_conflict_does_not_update_user_score_version(
    mock_merge, mock_save, mock_open, mock_exists, arrangement, ensemble, user, client
):
    mock_open.side_effect = lambda *_a, **_k: BytesIO(b"x")

    def merge_conflict(_base, _head, _user, output):
        with open(output, "wb") as out:
            out.write(b"conflict")
        raise MergeConflictException()

    mock_merge.side_effect = merge_conflict

    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    base_commit = Commit.latest_for_arrangement(arrangement)

    other_user = UserFactory()
    EnsembleUsershipFactory(ensemble=ensemble, user=other_user)
    other_client = client.__class__()
    other_client.force_authenticate(user=other_user)
    assert _post_commit(other_client, arrangement, "head.mscz", b"y").status_code == 200

    r = _post_commit(client, arrangement, "user.mscz", b"z")
    assert r.status_code == 200, r.content

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == base_commit.id

    tip = Commit.latest_for_arrangement(arrangement)
    assert tip.is_merge_conflict is True


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.open")
@patch("ensembles.serializers.default_storage.save")
@patch("ensembles.serializers.default_storage.delete")
@patch("musescore_score_diff.merge.three_way_merge_mscz")
def test_upload_stale_unexpected_merge_error_returns_complicated_merge(
    mock_merge, mock_delete, mock_save, mock_open, mock_exists, arrangement, ensemble, user, client
):
    mock_open.side_effect = lambda *_a, **_k: BytesIO(b"x")
    mock_merge.side_effect = RuntimeError("merge blew up")

    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    base_commit = Commit.latest_for_arrangement(arrangement)

    other_user = UserFactory()
    EnsembleUsershipFactory(ensemble=ensemble, user=other_user)
    other_client = client.__class__()
    other_client.force_authenticate(user=other_user)
    assert _post_commit(other_client, arrangement, "head.mscz", b"y").status_code == 200

    r = _post_commit(client, arrangement, "user.mscz", b"z")
    assert r.status_code == 409, r.content
    assert r.json()["merge_error"] == "Unable to merge scores. Use a force commit"

    head_commit = Commit.latest_for_arrangement(arrangement)
    assert head_commit.id != base_commit.id
    assert Commit.objects.filter(arrangement=arrangement).count() == 2

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == base_commit.id


@pytest.mark.django_db
@patch("ensembles.serializers.default_storage.save")
def test_check_score_version_error_when_stale(mock_save, arrangement, user, client):
    upload_url = reverse(
        "ensembles:arrangement-by-id-upload-new-commit", kwargs={"id": arrangement.id}
    )
    client.post(
        upload_url,
        data={
            "file": SimpleUploadedFile("first.mscz", b"x", content_type="application/octet-stream"),
        },
        format="multipart",
    )
    first_commit = Commit.latest_for_arrangement(arrangement)

    client.post(
        upload_url,
        data={
            "file": SimpleUploadedFile("second.mscz", b"y", content_type="application/octet-stream"),
        },
        format="multipart",
    )
    head_commit = Commit.latest_for_arrangement(arrangement)
    assert head_commit.id != first_commit.id

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    usv.commit = first_commit
    usv.save()

    check_url = reverse(
        "ensembles:arrangement-by-id-check-score-version", kwargs={"id": arrangement.id}
    )
    r = client.get(check_url)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "error"
    assert data["head_commit"] == head_commit.id
    assert data["user_download_commit"] == first_commit.id


@pytest.mark.django_db
@patch("ensembles.views.arrangement.default_storage.delete")
@patch("ensembles.views.arrangement.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.save")
def test_delete_latest_commit_clears_user_score_version_for_that_commit(
    mock_save, mock_exists, mock_delete, arrangement, user, client
):
    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    parent_commit = Commit.latest_for_arrangement(arrangement)

    assert _post_commit(client, arrangement, "second.mscz", b"y").status_code == 200
    tip = Commit.latest_for_arrangement(arrangement)
    assert tip.id != parent_commit.id

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == tip.id

    delete_url = reverse(
        "ensembles:arrangement-by-id-delete-commit",
        kwargs={"id": arrangement.id, "commit_id": tip.id},
    )
    r = client.delete(delete_url)
    assert r.status_code == 204

    usv.refresh_from_db()
    assert usv.commit_id is None
    assert Commit.latest_for_arrangement(arrangement).id == parent_commit.id

    check_url = reverse(
        "ensembles:arrangement-by-id-check-score-version", kwargs={"id": arrangement.id}
    )
    check = client.get(check_url)
    assert check.status_code == 200
    data = check.json()
    assert data["status"] == "error"
    assert data["head_commit"] == parent_commit.id
    assert data["user_download_commit"] is None


@pytest.mark.django_db
@patch("ensembles.views.arrangement.default_storage.delete")
@patch("ensembles.views.arrangement.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.save")
def test_delete_latest_commit_leaves_user_score_version_on_parent_unchanged(
    mock_save, mock_exists, mock_delete, arrangement, ensemble, user, client
):
    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    parent_commit = Commit.latest_for_arrangement(arrangement)

    other_user = UserFactory()
    EnsembleUsershipFactory(ensemble=ensemble, user=other_user)
    other_client = client.__class__()
    other_client.force_authenticate(user=other_user)
    assert _post_commit(other_client, arrangement, "second.mscz", b"y").status_code == 200
    tip = Commit.latest_for_arrangement(arrangement)

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == parent_commit.id

    delete_url = reverse(
        "ensembles:arrangement-by-id-delete-commit",
        kwargs={"id": arrangement.id, "commit_id": tip.id},
    )
    assert client.delete(delete_url).status_code == 204

    usv.refresh_from_db()
    assert usv.commit_id == parent_commit.id


@pytest.mark.django_db
@patch("ensembles.views.arrangement.default_storage.delete")
@patch("ensembles.views.arrangement.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.save")
def test_upload_after_deleted_tip_requires_download_before_merge(
    mock_save, mock_exists, mock_delete, arrangement, user, client
):
    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    parent_commit = Commit.latest_for_arrangement(arrangement)

    assert _post_commit(client, arrangement, "second.mscz", b"y").status_code == 200
    tip = Commit.latest_for_arrangement(arrangement)

    delete_url = reverse(
        "ensembles:arrangement-by-id-delete-commit",
        kwargs={"id": arrangement.id, "commit_id": tip.id},
    )
    assert client.delete(delete_url).status_code == 204

    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id is None
    assert Commit.objects.filter(arrangement=arrangement).count() == 1

    r = _post_commit(client, arrangement, "third.mscz", b"z")
    assert r.status_code == 400
    assert r.json()["client_error"] == "Download the latest score before uploading your changes."
    assert Commit.objects.filter(arrangement=arrangement).count() == 1


@pytest.mark.django_db
@patch("ensembles.views.arrangement.default_storage.delete")
@patch("ensembles.views.arrangement.default_storage.exists", return_value=True)
@patch("ensembles.serializers.default_storage.save")
def test_upload_after_deleted_tip_allows_force_commit(
    mock_save, mock_exists, mock_delete, arrangement, user, client
):
    assert _post_commit(client, arrangement, "first.mscz").status_code == 200
    parent_commit = Commit.latest_for_arrangement(arrangement)

    assert _post_commit(client, arrangement, "second.mscz", b"y").status_code == 200
    tip = Commit.latest_for_arrangement(arrangement)

    delete_url = reverse(
        "ensembles:arrangement-by-id-delete-commit",
        kwargs={"id": arrangement.id, "commit_id": tip.id},
    )
    assert client.delete(delete_url).status_code == 204

    r = _post_commit(client, arrangement, "third.mscz", b"z", force=True)
    assert r.status_code == 200, r.content

    new_tip = Commit.latest_for_arrangement(arrangement)
    assert new_tip.id != parent_commit.id
    usv = UserScoreVersion.objects.get(user=user, arrangement=arrangement)
    assert usv.commit_id == new_tip.id


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
    from ensembles.factories import PartAssetFactory
    from ensembles.models import PartName

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, mvt_no="1")
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)

    # Create parts in reverse order
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone", order=2)
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    for part in (part1, part2, part3):
        PartAssetFactory(arrangement_version=v, part_name=part)
    
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
    from ensembles.factories import PartAssetFactory
    from ensembles.models import PartName

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, mvt_no="1")
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)

    # Create parts: some with order, some without
    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute", order=0)
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet", order=1)
    # Create part without order (simulating old data)
    part3 = PartName.objects.create(ensemble=ensemble, display_name="Saxophone")
    part3.order = None
    part3.save()
    for part in (part1, part2, part3):
        PartAssetFactory(arrangement_version=v, part_name=part)
    
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


@pytest.mark.django_db
def test_part_name_matrix(ensemble, user, client):
    from ensembles.factories import PartAssetFactory, PartNameFactory
    from ensembles.models import PartName

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, title="Movement 1", mvt_no="1")
    v_latest = ArrangementVersionFactory(arrangement=arr, is_latest=True)
    ArrangementVersionFactory(arrangement=arr, is_latest=False)

    flute = PartNameFactory(ensemble=ensemble, display_name="Flute", order=0)
    score_name = PartNameFactory(ensemble=ensemble, display_name="Score", order=1)
    PartAssetFactory(arrangement_version=v_latest, part_name=flute, is_score=False)
    PartAssetFactory(arrangement_version=v_latest, part_name=score_name, is_score=True)

    url = reverse("ensembles:ensemble-part-name-matrix", kwargs={"slug": ensemble.slug})
    r = client.get(url)
    assert r.status_code == 200, r.content
    data = r.json()

    assert len(data["arrangements"]) == 1
    assert data["arrangements"][0]["id"] == arr.id
    assert len(data["columns"]) == 1
    assert data["columns"][0]["id"] == flute.id
    assert len(data["cells"]) == 1
    assert data["cells"][0]["part_name_id"] == flute.id
    assert data["cells"][0]["arrangement_id"] == arr.id


@pytest.mark.django_db
def test_part_name_matrix_excludes_names_without_latest_part_assets(
    ensemble, user, client
):
    from ensembles.factories import PartAssetFactory, PartNameFactory

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, mvt_no="1")
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)
    with_asset = PartNameFactory(ensemble=ensemble, display_name="Flute")
    without_asset = PartNameFactory(ensemble=ensemble, display_name="Unused")
    PartAssetFactory(arrangement_version=v, part_name=with_asset)

    url = reverse("ensembles:ensemble-part-name-matrix", kwargs={"slug": ensemble.slug})
    r = client.get(url)
    assert r.status_code == 200
    column_ids = [c["id"] for c in r.json()["columns"]]
    assert column_ids == [with_asset.id]
    assert without_asset.id not in column_ids


@pytest.mark.django_db
def test_part_name_matrix_merge_conflicts(ensemble, user, client):
    from ensembles.factories import PartAssetFactory, PartNameFactory

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, mvt_no="1")
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)
    name1, name2 = PartNameFactory.create_batch(2, ensemble=ensemble)
    PartAssetFactory(arrangement_version=v, part_name=name1)
    PartAssetFactory(arrangement_version=v, part_name=name2)

    url = reverse("ensembles:ensemble-part-name-matrix", kwargs={"slug": ensemble.slug})
    r = client.get(url)
    assert r.status_code == 200
    conflicts = r.json()["merge_conflicts"]
    assert [name1.id, name2.id] in conflicts or [name2.id, name1.id] in conflicts


@pytest.mark.django_db
def test_part_name_matrix_empty_ensemble(ensemble, user, client):
    ensemble.owner = user
    ensemble.save()

    url = reverse("ensembles:ensemble-part-name-matrix", kwargs={"slug": ensemble.slug})
    r = client.get(url)
    assert r.status_code == 200
    data = r.json()
    assert data["arrangements"] == []
    assert data["cells"] == []


@pytest.mark.django_db
def test_rename_part_name_as_admin(ensemble, user, client):
    from ensembles.factories import PartAssetFactory, PartNameFactory
    from ensembles.models.part_name_alias import PartNameAlias

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble)
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)
    part = PartNameFactory(ensemble=ensemble, display_name="Flute 1")
    PartAssetFactory(arrangement_version=v, part_name=part)

    url = reverse("ensembles:ensemble-rename-part-name", kwargs={"slug": ensemble.slug})
    r = client.post(
        url,
        data={"part_name_id": part.id, "display_name": "Flute"},
        content_type="application/json",
    )
    assert r.status_code == 200, r.content
    part.refresh_from_db()
    assert part.display_name == "Flute"
    assert PartNameAlias.objects.filter(
        ensemble=ensemble,
        arrangement=arr,
        alias_normalized=PartNameAlias.normalize("Flute 1"),
        canonical_part_name=part,
    ).exists()


@pytest.mark.django_db
def test_rename_part_name_duplicate_rejected(ensemble, user, client):
    from ensembles.models import PartName

    ensemble.owner = user
    ensemble.save()

    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute")
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Clarinet")

    url = reverse("ensembles:ensemble-rename-part-name", kwargs={"slug": ensemble.slug})
    r = client.post(
        url,
        data={"part_name_id": part2.id, "display_name": "Flute"},
        content_type="application/json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_rename_part_name_as_non_admin(ensemble, user, client):
    from ensembles.models import PartName, EnsembleUsership

    part = PartName.objects.create(ensemble=ensemble, display_name="Flute")
    non_admin = UserFactory()
    EnsembleUsership.objects.create(ensemble=ensemble, user=non_admin)

    url = reverse("ensembles:ensemble-rename-part-name", kwargs={"slug": ensemble.slug})
    client.force_login(non_admin)
    r = client.post(
        url,
        data={"part_name_id": part.id, "display_name": "Flute I"},
        content_type="application/json",
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_merge_part_names_as_non_admin(ensemble, user, client):
    from ensembles.models import PartName, EnsembleUsership

    part1 = PartName.objects.create(ensemble=ensemble, display_name="Flute")
    part2 = PartName.objects.create(ensemble=ensemble, display_name="Flute I")
    non_admin = UserFactory()
    EnsembleUsership.objects.create(ensemble=ensemble, user=non_admin)

    url = reverse("ensembles:ensemble-merge-part-names", kwargs={"slug": ensemble.slug})
    client.force_login(non_admin)
    r = client.post(
        url,
        data={"first_id": part1.id, "second_id": part2.id},
        content_type="application/json",
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_part_names_include_arrangement_ids(ensemble, user, client):
    from ensembles.factories import PartAssetFactory, PartNameFactory

    ensemble.owner = user
    ensemble.save()

    arr = ArrangementFactory(ensemble=ensemble, title="Song A")
    v = ArrangementVersionFactory(arrangement=arr, is_latest=True)
    part = PartNameFactory(ensemble=ensemble, display_name="Flute")
    PartAssetFactory(arrangement_version=v, part_name=part)

    url = reverse("ensembles:ensemble-detail", kwargs={"slug": ensemble.slug})
    r = client.get(url)
    assert r.status_code == 200
    part_names = r.json()["part_names"]
    flute_entry = next(p for p in part_names if p["id"] == part.id)
    assert flute_entry["arrangement_ids"] == [arr.id]
    assert flute_entry["arrangements"] == ["Song A"]