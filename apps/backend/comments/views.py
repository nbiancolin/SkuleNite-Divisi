from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comments.models import ArrangementVersionComment, ArrangementVersionCommentThread
from comments.permissions import get_accessible_versions_for_user
from comments.serializers import (
    ArrangementVersionCommentThreadSerializer,
    CreateCommentSerializer,
    CreateCommentThreadSerializer,
)


def _get_accessible_version_or_404(user, version_id):
    return get_object_or_404(get_accessible_versions_for_user(user), id=version_id)


def _get_accessible_thread_or_404(user, version_id, thread_id):
    _get_accessible_version_or_404(user, version_id)
    return get_object_or_404(
        ArrangementVersionCommentThread.objects.select_related("arrangement_version"),
        id=thread_id,
        arrangement_version_id=version_id,
    )


class ArrangementVersionCommentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, version_id):
        _get_accessible_version_or_404(request.user, version_id)
        threads = ArrangementVersionCommentThread.objects.filter(
            arrangement_version_id=version_id
        ).select_related("created_by", "resolved_by")
        serializer = ArrangementVersionCommentThreadSerializer(threads, many=True)
        return Response({"threads": serializer.data})


class ArrangementVersionCreateThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id):
        version = _get_accessible_version_or_404(request.user, version_id)
        serializer = CreateCommentThreadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            thread = ArrangementVersionCommentThread.objects.create(
                arrangement_version=version,
                created_by=request.user,
                page_number=payload["page_number"],
                x=payload["x"],
                y=payload["y"],
            )
            ArrangementVersionComment.objects.create(
                thread=thread,
                author=request.user,
                body=payload["body"],
            )

        return Response(
            ArrangementVersionCommentThreadSerializer(thread).data, status=status.HTTP_201_CREATED
        )


class ArrangementVersionCreateCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id, thread_id):
        thread = _get_accessible_thread_or_404(request.user, version_id, thread_id)
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = ArrangementVersionComment.objects.create(
            thread=thread,
            author=request.user,
            body=serializer.validated_data["body"],
        )
        return Response(
            {
                "id": comment.id,
                "body": comment.body,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
            },
            status=status.HTTP_201_CREATED,
        )


class ArrangementVersionResolveThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id, thread_id):
        thread = _get_accessible_thread_or_404(request.user, version_id, thread_id)
        thread.status = ArrangementVersionCommentThread.Status.RESOLVED
        thread.resolved_by = request.user
        thread.resolved_at = timezone.now()
        thread.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])
        return Response(ArrangementVersionCommentThreadSerializer(thread).data)


class ArrangementVersionReopenThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id, thread_id):
        thread = _get_accessible_thread_or_404(request.user, version_id, thread_id)
        thread.status = ArrangementVersionCommentThread.Status.OPEN
        thread.resolved_by = None
        thread.resolved_at = None
        thread.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])
        return Response(ArrangementVersionCommentThreadSerializer(thread).data)
