from logging import getLogger

from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ensembles.models import (
    Arrangement,
    Commit,
    EnsembleUsership,
    UserScoreVersion,
)
from ensembles.serializers import (
    ArrangementSerializer,
    ArrangementVersionSerializer,
    CommitSerializer,
    CreateArrangementCommitSerializer,
)

LOGGER = getLogger("ensembles_views")


class BaseArrangementViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Arrangement.objects.none()

        return Arrangement.objects.filter(
            Q(ensemble__owner=user) | Q(ensemble__userships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        ensemble = serializer.validated_data["ensemble"]
        user = self.request.user

        if ensemble.owner != user and not EnsembleUsership.objects.filter(ensemble=ensemble, user=user).exists():
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this ensemble.")

        serializer.save()

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, *args, **kwargs):
        arr = self.get_object()
        versions = arr.versions.all()
        serializer = ArrangementVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="commits")
    def commits(self, request, *args, **kwargs):
        arr = self.get_object()
        commits = arr.commits.all().order_by("-id")
        serializer = CommitSerializer(commits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def check_score_version(self, request, *args, **kwargs):
        user = request.user
        arr = self.get_object()

        head_commit = Commit.latest_for_arrangement(arr)
        if head_commit is None:
            LOGGER.warning(
                "Tried to check score version on an arrangement without any commits. Returning OK"
            )
            return Response({"status": "ok"})

        try:
            user_download_commit = UserScoreVersion.objects.get(user=user, arrangement=arr).commit
        except UserScoreVersion.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "head_commit": head_commit.id,
                    "user_download_commit": None,
                }
            )

        if user_download_commit is None or head_commit.id != user_download_commit.id:
            return Response(
                {
                    "status": "error",
                    "head_commit": head_commit.id,
                    "user_download_commit": (
                        user_download_commit.id if user_download_commit else None
                    ),
                }
            )

        return Response({"status": "ok"})

    @action(detail=True, methods=["post"], url_path="new-commit")
    def upload_new_commit(self, request, *args, **kwargs):
        arr = self.get_object()
        serializer = CreateArrangementCommitSerializer(
            data=request.data, context={"arrangement": arr, "user": request.user}
        )
        serializer.is_valid(raise_exception=True)

        r = serializer.save()
        if error := r.get("error"):
            return Response(error, status=500)

        if r.get("merge_error"):
            return Response(r, status=409)
        
        if r.get("client_error"):
            return Response(r, status=400)

        s = ArrangementSerializer(self.get_object())
        return Response(s.data)

    def _commit_mscz_file_response(self, commit: Commit, arrangement: Arrangement, record_download: bool):
        if commit.arrangement_id != arrangement.id:
            return Response(
                {"detail": "Commit does not belong to this arrangement."},
                status=status.HTTP_404_NOT_FOUND,
            )
        key = commit.mscz_file_key
        if not default_storage.exists(key):
            return Response(
                {"detail": "MSCZ file not found in storage."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if record_download:
            UserScoreVersion.record_for_user(self.request.user, arrangement, commit)
        file_handle = default_storage.open(key, "rb")
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=commit.file_name,
            content_type="application/zip",
        )

    @action(detail=True, methods=["get"], url_path="download-latest-commit-mscz")
    def download_latest_commit_mscz(self, request, *args, **kwargs):
        arr = self.get_object()
        latest = Commit.latest_for_arrangement(arr)
        if latest is None:
            return Response(
                {"detail": "No commits for this arrangement."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return self._commit_mscz_file_response(latest, arr, record_download=True)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"commits/(?P<commit_id>[^/.]+)/download-mscz",
    )
    def download_commit_mscz(self, request, commit_id=None, *args, **kwargs):
        arr = self.get_object()
        try:
            commit = Commit.objects.get(pk=commit_id, arrangement=arr)
        except (Commit.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Commit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        record_download = request.query_params.get("record_download", "true").lower() != "false"
        return self._commit_mscz_file_response(commit, arr, record_download=record_download)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"commits/(?P<commit_id>[^/.]+)",
    )
    def delete_commit(self, request, commit_id=None, *args, **kwargs):
        arr = self.get_object()
        try:
            commit = Commit.objects.get(pk=commit_id, arrangement=arr)
        except (Commit.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Commit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not commit.is_latest_commit:
            return Response(
                {"detail": "Only the latest commit can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if commit.has_version:
            return Response(
                {"detail": "Cannot delete a commit that has an arrangement version."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = commit.mscz_file_key
        if default_storage.exists(key):
            default_storage.delete(key)

        UserScoreVersion.clear_commit_references(commit)
        commit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArrangementViewSet(BaseArrangementViewSet):
    lookup_field = "slug"


class ArrangementByIdViewSet(BaseArrangementViewSet):
    lookup_field = "id"
