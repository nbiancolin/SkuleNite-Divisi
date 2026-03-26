import pytest


from apps.backend.ensembles.models.commit import Commit

@pytest.mark.django_db
def test_create_new_commit_new_arrangement(arrangement):

    new = Commit.create_new_commit(arrangement, create_kwargs={"file_name": "abc123.mscz"})

    assert new.is_initial_commit is True
    assert new.is_latest_commit is True


@pytest.mark.django_db
def test_create_new_commit_works_with_existing_commit(arrangement):

    first_commit = Commit.create_new_commit(arrangement, create_kwargs={"file_name": "abc123.mscz"})

    new = Commit.create_new_commit(arrangement, create_kwargs={"file_name": "abc123.mscz"})

    first_commit.refresh_from_db()

    assert new.is_latest_commit is True
    
    assert first_commit.is_initial_commit is True
    assert first_commit.is_latest_commit is False