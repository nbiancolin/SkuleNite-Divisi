import pytest

from comments.models import ArrangementVersionCommentThread
from ensembles.factories import ArrangementFactory, ArrangementVersionFactory, EnsembleFactory, EnsembleUsershipFactory, UserFactory


@pytest.mark.django_db
def test_member_can_create_reply_resolve_and_reopen_comment_thread(client):
    owner = UserFactory()
    ensemble = EnsembleFactory(owner=owner)
    member = UserFactory()
    EnsembleUsershipFactory(user=member, ensemble=ensemble)
    arrangement = ArrangementFactory(ensemble=ensemble)
    version = ArrangementVersionFactory(arrangement=arrangement)

    client.force_login(member)

    create_thread_response = client.post(
        f"/api/arrangementversions/{version.id}/comments/threads/",
        data={"page_number": 1, "x": 0.25, "y": 0.5, "body": "Please adjust articulation."},
        content_type="application/json",
    )
    assert create_thread_response.status_code == 201, create_thread_response.content
    thread_id = create_thread_response.json()["id"]

    create_reply_response = client.post(
        f"/api/arrangementversions/{version.id}/comments/threads/{thread_id}/messages/",
        data={"body": "Following up with a second note."},
        content_type="application/json",
    )
    assert create_reply_response.status_code == 201, create_reply_response.content

    resolve_response = client.post(
        f"/api/arrangementversions/{version.id}/comments/threads/{thread_id}/resolve/",
        content_type="application/json",
    )
    assert resolve_response.status_code == 200, resolve_response.content

    thread = ArrangementVersionCommentThread.objects.get(id=thread_id)
    assert thread.status == ArrangementVersionCommentThread.Status.RESOLVED
    assert thread.resolved_by_id == member.id
    assert thread.resolved_at is not None

    reopen_response = client.post(
        f"/api/arrangementversions/{version.id}/comments/threads/{thread_id}/reopen/",
        content_type="application/json",
    )
    assert reopen_response.status_code == 200, reopen_response.content

    thread.refresh_from_db()
    assert thread.status == ArrangementVersionCommentThread.Status.OPEN
    assert thread.resolved_by is None
    assert thread.resolved_at is None


@pytest.mark.django_db
def test_non_member_cannot_access_comments(client):
    owner = UserFactory()
    ensemble = EnsembleFactory(owner=owner)
    non_member = UserFactory()
    arrangement = ArrangementFactory(ensemble=ensemble)
    version = ArrangementVersionFactory(arrangement=arrangement)

    client.force_login(non_member)
    response = client.get(f"/api/arrangementversions/{version.id}/comments/")
    assert response.status_code == 404
