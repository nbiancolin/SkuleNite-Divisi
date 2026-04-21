from django.urls import path

from comments.views import (
    ArrangementVersionCommentListView,
    ArrangementVersionCreateCommentView,
    ArrangementVersionCreateThreadView,
    ArrangementVersionReopenThreadView,
    ArrangementVersionResolveThreadView,
)


urlpatterns = [
    path(
        "arrangementversions/<int:version_id>/comments/",
        ArrangementVersionCommentListView.as_view(),
        name="arrangement-version-comments-list",
    ),
    path(
        "arrangementversions/<int:version_id>/comments/threads/",
        ArrangementVersionCreateThreadView.as_view(),
        name="arrangement-version-comments-create-thread",
    ),
    path(
        "arrangementversions/<int:version_id>/comments/threads/<int:thread_id>/messages/",
        ArrangementVersionCreateCommentView.as_view(),
        name="arrangement-version-comments-create-message",
    ),
    path(
        "arrangementversions/<int:version_id>/comments/threads/<int:thread_id>/resolve/",
        ArrangementVersionResolveThreadView.as_view(),
        name="arrangement-version-comments-resolve-thread",
    ),
    path(
        "arrangementversions/<int:version_id>/comments/threads/<int:thread_id>/reopen/",
        ArrangementVersionReopenThreadView.as_view(),
        name="arrangement-version-comments-reopen-thread",
    ),
]
