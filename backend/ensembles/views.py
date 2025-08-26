from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction
from django.conf import settings

from .tasks import prep_and_export_mscz, export_arrangement_version

from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import (
    EnsembleSerializer,
    ArrangementSerializer,
    CreateArrangementVersionMsczSerializer,
    ArrangementVersionDownloadLinksSeiializer,
)
from logging import getLogger

import os

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


class ArrangementViewSet(BaseArrangementViewSet):
    lookup_field = "slug"


class ArrangementByIdViewSet(BaseArrangementViewSet):
    lookup_field = "id"


class ArrangementVersionViewSet(viewsets.ModelViewSet):
    queryset = ArrangementVersion.objects.all()
    serializer_class = ArrangementSerializer


"""
How arrangement versions should work
- Arranger opens their ensemble home page
- Selects the arrangememnt that they are working on
- On the arrangement page, they select "Upload New Version"
- Select version type, and style settings, then upload new arrangement version
BE:
- Create New Version, FE sends version type (major, minor, hotfix) and arrangement pk
- BE creates version, sends MSCZ file to be processed, then updates arranementVersion with file paths
    - if new version, gets prev version and umps it (how?)
"""


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

        # TODO wrap in transaction
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
            )

            version.save(
                version_type=serializer.validated_data["version_type"],
            )

        uploaded_file = serializer.validated_data["file"]
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not os.path.exists(version.mscz_file_location):
            os.makedirs(version.mscz_file_location)

        with open(version.mscz_file_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # format mscz
        if serializer.validated_data["format_parts"]:
            prep_and_export_mscz.delay(version.pk)
        else:
            # just export
            export_arrangement_version.delay(version.pk)

        return Response(
            {"message": "File Uploaded Successfully", "version_id": version.pk},
            status=status.HTTP_200_OK,
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

        relative_raw_path = os.path.relpath(version.mscz_file_path, settings.MEDIA_ROOT)
        relative_output_path = os.path.relpath(
            version.output_file_path, settings.MEDIA_ROOT
        )
        relative_score_parts_path = os.path.relpath(
            version.score_parts_pdf_path, settings.MEDIA_ROOT
        )
        raw_mscz_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_raw_path.replace("\\", "/")
        )
        processed_mscz_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_output_path.replace("\\", "/")
        )

        output_score_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_score_parts_path.replace("\\", "/")
        )

        return Response(
            {
                "message": "Successfully created download links",
                "is_processing": version.is_processing,
                "error": version.error_on_export,
                "raw_mscz_url": raw_mscz_url,
                "processed_mscz_url": processed_mscz_url,
                "score_parts_pdf_link": output_score_url,
            }
        )
