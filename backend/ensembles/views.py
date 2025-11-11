from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.files.storage import default_storage


from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import (
    EnsembleSerializer,
    ArrangementSerializer,
    ArrangementVersionSerializer,
    CreateArrangementVersionMsczSerializer,
    ComputeDiffSerializer,
)
from logging import getLogger

logger = getLogger("EnsembleViews")


class EnsembleViewSet(viewsets.ModelViewSet):
    queryset = Ensemble.objects.all()
    serializer_class = EnsembleSerializer
    lookup_field = "slug"  # use slug instead of pk

    @action(detail=True, methods=["get"], url_path="arrangements")
    def arrangements(self, request, slug=None):
        """Return all arrangements for a specific ensemble."""
        ensemble = self.get_object()
        arrangements = ensemble.arrangements.all()
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)


class BaseArrangementViewSet(viewsets.ModelViewSet):
    queryset = Arrangement.objects.all()
    serializer_class = ArrangementSerializer

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
    queryset = ArrangementVersion.objects.all()
    serializer_class = ArrangementSerializer

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
        }

        # Only include URLs for files that actually exist
        if not default_storage.exists(version.mscz_file_key):
            response_data["raw_mscz_url"] = None

        if not default_storage.exists(version.output_file_key):
            response_data["processed_mscz_url"] = None

        if not default_storage.exists(version.score_parts_pdf_key):
            response_data["score_parts_pdf_link"] = None

        return Response(response_data)

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
