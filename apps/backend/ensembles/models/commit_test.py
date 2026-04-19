import pytest


from ensembles.models.commit import Commit

@pytest.mark.django_db
def test_create_new_commit_new_arrangement(arrangement, user):

    new = Commit.create_new_commit(
        arrangement,
        created_by_user=user,
        create_kwargs={"file_name": "abc123.mscz", "message": "init"},
    )

    assert new.is_initial_commit is True
    assert new.is_latest_commit is True


@pytest.mark.django_db
def test_create_new_commit_sets_created_by_on_follow_up_commit(arrangement, user):
    first = Commit.create_new_commit(
        arrangement,
        created_by_user=user,
        create_kwargs={"file_name": "a.mscz", "message": "first"},
    )
    second = Commit.create_new_commit(
        arrangement,
        created_by_user=user,
        create_kwargs={"file_name": "b.mscz", "message": "second"},
    )
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.created_by_id == user.id
    assert second.created_by_id == user.id


@pytest.mark.django_db
def test_create_new_commit_works_with_existing_commit(arrangement, user):

    first_commit = Commit.create_new_commit(
        arrangement,
        created_by_user=user,
        create_kwargs={"file_name": "abc123.mscz", "message": "first"},
    )

    new = Commit.create_new_commit(
        arrangement,
        user,
        create_kwargs={"file_name": "abc123.mscz", "message": "second"},
    )

    first_commit.refresh_from_db()

    assert new.is_latest_commit is True
    
    assert first_commit.is_initial_commit is True
    assert first_commit.is_latest_commit is False


@pytest.mark.django_db
def test_latest_for_arrangement_returns_tip(arrangement, user):
    first_commit = Commit.create_new_commit(
        arrangement, created_by_user=user, create_kwargs={"file_name": "a.mscz", "message": "m1"}
    )
    second = Commit.create_new_commit(
        arrangement, created_by_user=user, create_kwargs={"file_name": "b.mscz", "message": "m2"}
    )
    assert Commit.latest_for_arrangement(arrangement) == second
    assert Commit.latest_for_arrangement(arrangement) != first_commit


@pytest.mark.django_db
def test_latest_for_arrangement_empty(arrangement):
    assert Commit.latest_for_arrangement(arrangement) is None