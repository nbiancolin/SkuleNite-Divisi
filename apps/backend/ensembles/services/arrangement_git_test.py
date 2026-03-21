import pytest
from django.test import override_settings

from ensembles.factories import ArrangementFactory
from ensembles.git import init_repo


@pytest.mark.django_db
def test_git_repo_delete_cleans_up_repo_files(tmp_path):
    arrangement_root = tmp_path / "arrangement_repos"

    with override_settings(ARRANGEMENT_GIT_ROOT=str(arrangement_root)):
        arrangement = ArrangementFactory()
        repo_path = init_repo(arrangement)

        git_repo = arrangement.git_repo
        assert git_repo.repo_path == repo_path
        assert arrangement_root.exists()
        assert arrangement_root.joinpath(f"arr_{arrangement.id}.git").exists()

        git_repo.delete()

        assert not arrangement_root.joinpath(f"arr_{arrangement.id}.git").exists()
