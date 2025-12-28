from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes

from django.core.files.storage import default_storage
from django.db.models import Q

from .models import Arrangement, Ensemble, ArrangementVersion, EnsembleUsership
from .serializers import (
    EnsembleSerializer,
    ArrangementSerializer,
    ArrangementVersionSerializer,
    CreateArrangementVersionMsczSerializer,
    ComputeDiffSerializer,
)
from logging import getLogger
from django.db.models.expressions import RawSQL

from ensembles.tasks import export_arrangement_version


class EnsembleViewSet(viewsets.ModelViewSet):
    serializer_class = EnsembleSerializer
    lookup_field = "slug"  # use slug instead of pk
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter ensembles to only those the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return Ensemble.objects.none()
        
        # Get ensembles where user is owner or has usership
        return Ensemble.objects.filter(
            Q(owner=user) | Q(userships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """Set the owner when creating an ensemble"""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="arrangements")
    def arrangements(self, request, slug=None):
        """Return all arrangements for a specific ensemble."""
        ensemble = self.get_object()
        # Verify user has access
        if not self._has_access(ensemble, request.user):
            return Response(
                {"detail": "You do not have access to this ensemble."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        arrangements = (
            ensemble.arrangements
            .annotate(
                first_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
                second_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^[0-9]+(?:-|m)([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
            )
            .order_by("first_num", "second_num", "mvt_no")
        )
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)

    def _has_access(self, ensemble, user):
        """Check if user has access to ensemble"""
        return ensemble.owner == user or EnsembleUsership.objects.filter(
            ensemble=ensemble, user=user
        ).exists()


class BaseArrangementViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter arrangements to only those in ensembles the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return Arrangement.objects.none()
        
        # Get arrangements from ensembles where user is owner or has usership
        return Arrangement.objects.filter(
            Q(ensemble__owner=user) | Q(ensemble__userships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """Verify user has access to the ensemble before creating arrangement"""
        ensemble = serializer.validated_data['ensemble']
        user = self.request.user
        
        if ensemble.owner != user and not EnsembleUsership.objects.filter(
            ensemble=ensemble, user=user
        ).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this ensemble.")
        
        serializer.save()

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, *args, **kwargs):
        """Return all versions for an arrangement"""
        arr = self.get_object()
        versions = arr.versions.all()
        serializer = ArrangementVersionSerializer(versions, many=True)
        return Response(serializer.data)


class ArrangementViewSet(BaseArrangementViewSet):
    lookup_field = "slug"


class ArrangementByIdViewSet(BaseArrangementViewSet):
    lookup_field = "id"


class ArrangementVersionViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter versions to only those in ensembles the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return ArrangementVersion.objects.none()
        
        # Get versions from arrangements in ensembles where user is owner or has usership
        return ArrangementVersion.objects.filter(
            Q(arrangement__ensemble__owner=user) | Q(arrangement__ensemble__userships__user=user)
        ).distinct()

    @action(detail=False, methods=["post"], url_path="upload")
    def upload_arrangement_version(self, request):
        serializer = CreateArrangementVersionMsczSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = serializer.save()
        if "error" in res.keys():
            return Response(
                {"message": "Error", "details": res["error"]}
            )

        return Response(
            {"message": "File Uploaded Successfully", "version_id": res["version_id"]},
            status=status.HTTP_202_ACCEPTED,
        )
    
    @action(detail=True, methods=["get"])
    def get_download_links(self, request, pk=None):
        version = self.get_object()

        response_data = {
            "message": "Successfully created download links",
            "is_processing": version.is_processing,
            "error": version.error_on_export,
            "raw_mscz_url": request.build_absolute_uri(version.mscz_file_url),
            "processed_mscz_url": request.build_absolute_uri(version.output_file_url),
            "score_parts_pdf_link": request.build_absolute_uri(
                version.score_parts_pdf_url
            ),
            "mp3_link": request.build_absolute_uri(version.audio_file_url)
        }

        # Only include URLs for files that actually exist
        if not default_storage.exists(version.mscz_file_key):
            response_data["raw_mscz_url"] = None

        if not default_storage.exists(version.output_file_key):
            response_data["processed_mscz_url"] = None

        if not default_storage.exists(version.score_parts_pdf_key):
            response_data["score_parts_pdf_link"] = None

        return Response(response_data)
    
    @action(detail=True, methods=["post"])
    def trigger_audio_export(self, request, pk=None):
        version = self.get_object()
        
        match version.audio_state:
            case ArrangementVersion.AudioStatus.NONE:
                # Trigger export
                version.audio_state = ArrangementVersion.AudioStatus.PROCESSING
                version.save(update_fields=["audio_state"])
                export_arrangement_version.delay(version.id, action="mp3")
                return Response({}, status=status.HTTP_202_ACCEPTED)
            case ArrangementVersion.AudioStatus.PROCESSING:
                return Response({}, status=status.HTTP_102_PROCESSING)
            case ArrangementVersion.AudioStatus.COMPLETE:
                return Response({"mp3_link": request.build_absolute_uri(version.audio_file_url)})
            case ArrangementVersion.AudioStatus.ERROR:
                return Response({"error": "Error on export of audio file"}, status=500)


class ComputeDiffView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ComputeDiffSerializer(data=request.data)
        if not serializer.is_valid(raise_exception=True):
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        res = serializer.save()
        res["file_url"] = request.build_absolute_uri(res["file_url"])
        if res["status"] == "completed":
            return Response(res, status=status.HTTP_200_OK)
        else:
            return Response(res, status=status.HTTP_202_ACCEPTED)

    def get(self, request, *args, **kwargs):
        serializer = ComputeDiffSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        res = serializer.save()
        res["file_url"] = request.build_absolute_uri(res["file_url"])
        if res["status"] == "completed":
            return Response(res, status=status.HTTP_200_OK)
        else:
            return Response(res, status=status.HTTP_202_ACCEPTED)
