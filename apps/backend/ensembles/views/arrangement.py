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

        try:
            head_commit = Commit.latest_for_arrangement(arr)
            user_download_commit = UserScoreVersion.objects.get(user=user, arrangement=arr).commit

            if head_commit.id != user_download_commit.id:
                return Response(
                    {
                        "status": "error",
                        "head_commit": head_commit.id,
                        "user_download_commit": user_download_commit.id,
                    }
                )
        except Commit.DoesNotExist:
            # arrangement with no commits
            LOGGER.warning("Tried to check score version on an arrangement without any commits. Returning OK")
            return Response({"status": "ok"})
        except UserScoreVersion.DoesNotExist:
            return Response(
                    {
                        "status": "error",
                        "head_commit": head_commit.id,
                        "user_download_commit": user_download_commit.id,
                    }
                )

        except Exception as e:
            LOGGER.warning(f"Error in Check Score Version:\n {e}")
        finally:
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

        try:
            usv = UserScoreVersion.objects.get(user=request.user, arrangement=arr)
            usv.commit = r["commit"]
            usv.save()

        except UserScoreVersion.DoesNotExist:
            UserScoreVersion.objects.create(user=request.user, arrangement=arr, commit=r["commit"])

        s = ArrangementSerializer(self.get_object())
        return Response(s.data)

    @action(detail=True, methods=["get"], url_path="download-latest-commit-mscz")
    def download_latest_commit_mscz(self, request, *args, **kwargs):
        arr = self.get_object()
        latest = Commit.latest_for_arrangement(arr)
        if latest is None:
            return Response(
                {"detail": "No commits for this arrangement."},
                status=status.HTTP_404_NOT_FOUND,
            )
        key = latest.mscz_file_key
        if not default_storage.exists(key):
            return Response(
                {"detail": "MSCZ file not found in storage."},
                status=status.HTTP_404_NOT_FOUND,
            )
        UserScoreVersion.objects.update_or_create(
            user=request.user,
            arrangement=arr,
            defaults={"commit": latest},
        )
        file_handle = default_storage.open(key, "rb")
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=latest.file_name,
            content_type="application/zip",
        )


class ArrangementViewSet(BaseArrangementViewSet):
    lookup_field = "slug"


class ArrangementByIdViewSet(BaseArrangementViewSet):
    lookup_field = "id"
