from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction
from django.core.files.storage import default_storage

from .tasks import prep_and_export_mscz, export_arrangement_version

from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import (
    EnsembleSerializer,
    ArrangementSerializer,
    ArrangementVersionSerializer,
    CreateArrangementVersionMsczSerializer,
    ArrangementVersionDownloadLinksSeiializer,
    ComputeDiffSerializer,
)
from logging import getLogger

import io

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


class UploadArrangementVersionMsczView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateArrangementVersionMsczSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        arrangement_id = serializer.validated_data["arrangement_id"]
        try:
            arr = Arrangement.objects.get(id=arrangement_id)
        except Arrangement.DoesNotExist:
            return Response(
                {
                    "message": "Provided arrangement ID does not exist",
                    "arrangement_id": arrangement_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            version = ArrangementVersion.objects.create(
                arrangement=arr,
                file_name=serializer.validated_data["file"].name,
                num_measures_per_line_score=serializer.validated_data[
                    "num_measures_per_line_score"
                ],
                num_measures_per_line_part=serializer.validated_data[
                    "num_measures_per_line_part"
                ],
                num_lines_per_page=serializer.validated_data["num_lines_per_page"]
            )

            version.save(
                version_type=serializer.validated_data["version_type"],
            )

        uploaded_file = serializer.validated_data["file"]
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Save file to storage using the storage key
        try:
            # Create a file-like object from the uploaded file
            file_content = b""
            for chunk in uploaded_file.chunks():
                file_content += chunk

            # Save to storage using the key
            default_storage.save(version.mscz_file_key, io.BytesIO(file_content))
            logger.info(f"Saved file to storage: {version.mscz_file_key}")

        except Exception as e:
            logger.error(f"Failed to save file to storage: {e}")
            # Clean up the version if file save failed
            version.delete()
            return Response(
                {"error": "Failed to save file to storage"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Format mscz if selected by FE
        if serializer.validated_data["format_parts"]:
            prep_and_export_mscz.delay(version.pk)
        else:
            # Just export
            export_arrangement_version.delay(version.pk)

        # epxort MXL for diff calculation
        export_arrangement_version(version.pk, action="mxl")

        return Response(
            {"message": "File Uploaded Successfully", "version_id": version.pk},
            status=status.HTTP_202_ACCEPTED,
        )


class ArrangementVersionDownloadLinks(APIView):
    def get(self, request, *args, **kwargs):
        serializer = ArrangementVersionDownloadLinksSeiializer(data=request.GET)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            version = ArrangementVersion.objects.get(
                id=serializer.validated_data["version_id"]
            )
        except ArrangementVersion.DoesNotExist:
            return Response(
                {"message": "Provided version ID does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Use the new URL properties from the model
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
