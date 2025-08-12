from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction
from django.conf import settings

from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import (
    CreateEnsembleSerializer,
    CreateArrangementSerializer,
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


class ArrangementViewSet(viewsets.ModelViewSet):
    queryset = Arrangement.objects.all()
    serializer_class = ArrangementSerializer
    lookup_field = "slug"


class ArrangementByIdViewSet(viewsets.ModelViewSet):
    queryset = Arrangement.objects.all()
    serializer_class = ArrangementSerializer
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

        return Response(
            {"message": "File Uploaded Successfully", "version_id": version.id},
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
        raw_mscz_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_raw_path.replace("\\", "/")
        )
        score_pdf_url = request.build_absolute_uri(
            settings.MEDIA_URL + relative_output_path.replace("\\", "/")
        )

        return Response(
            {
                "message": "Successfully created download links",
                "raw_mscz_url": raw_mscz_url,
                "score_pdf_url": score_pdf_url,
            }
        )


"""
Ideal URL Patterns
BASE = http://divisi.nbiancolin.ca/divisi

FE URL Patterns
View (all arrangements in) Ensemble: BASE/ensembles/<name>
(Alt: BASe/home) (If we restrict users to only be in one ensemble at a time)
View Arrangement: BAr: BASE/arrangements/<pk> (haven't decided which is best)
(Alt: BASE/arr/<title> orsion:  BASE/arrangements/<pk>
Upload New Arrangement <Arr-url>/upload



BE Url Patterns don't really matter, they're just APIs, so IG model viewsets for all of them
"""

# OLD: TODO remove


class CreateEnsembleView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateEnsembleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ens = Ensemble.objects.create(name=serializer.validated_data["name"])

        return Response(
            {"message": "Ensemble Created Successfully", "name_slug": ens.slug},
            status=status.HTTP_200_OK,
        )


class CreateArrangementView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateArrangementSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ens = Ensemble.objects.get(name=serializer.validated_data["ensemble_name"])

        arr = Arrangement.objects.create(
            ensemble_id=ens.pk,
            title=serializer.validated_data["title"],
            subtitle=serializer.validated_data.get("subtitle"),
            act_number=serializer.validated_data.get("act_number"),
            piece_number=serializer.validated_data["piece_number"],
        )

        return Response(
            {"message": "Ensemble Created Successfully", "title_slug": arr.slug},
            status=status.HTTP_200_OK,
        )

        arrangements = ens.arrangements.all()  # TODO: Check if this is a legit error
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)
