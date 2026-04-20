from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ensembles.models import ArrangementVersion, PartAsset
from ensembles.serializers import (
    ArrangementVersionSerializer,
    CreateArrangementVersionFromCommitSerializer,
    CreateArrangementVersionMsczSerializer,
)
from ensembles.tasks import export_arrangement_version


class ArrangementVersionViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ArrangementVersion.objects.none()

        return ArrangementVersion.objects.filter(
            Q(arrangement__ensemble__owner=user) | Q(arrangement__ensemble__userships__user=user)
        ).distinct()

    @action(detail=False, methods=["post"])
    def create_from_commit(self, request):
        serializer = CreateArrangementVersionFromCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = serializer.save()

        return Response(res, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload_arrangement_version(self, request):
        serializer = CreateArrangementVersionMsczSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = serializer.save()
        if "error" in res.keys():
            return Response({"message": "Error", "details": res["error"]})

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
            "score_parts_pdf_link": None,
            "score_pdf_url": None,
            "mp3_link": request.build_absolute_uri(version.audio_file_url),
            "combined_parts_pdf_url": None,
            "download_all_parts_url": request.build_absolute_uri(version.combined_parts_pdf_url),
            "parts": [],
        }

        if not default_storage.exists(version.mscz_file_key):
            response_data["raw_mscz_url"] = None

        if not default_storage.exists(version.output_file_key):
            response_data["processed_mscz_url"] = None

        parts = PartAsset.objects.filter(arrangement_version=version)
        if parts.exists():
            for part in parts:
                if default_storage.exists(part.file_key):
                    part_data = {
                        "id": part.id,
                        "name": part.name,
                        "is_score": part.is_score,
                        "file_url": request.build_absolute_uri(part.file_url),
                        "download_url": request.build_absolute_uri(
                            f"/api/arrangementversions/{version.id}/download_part/{part.id}/"
                        ),
                    }
                    response_data["parts"].append(part_data)

                    if part.is_score:
                        response_data["score_pdf_url"] = part_data["file_url"]
                        response_data["score_parts_pdf_link"] = part_data["file_url"]
        else:
            if default_storage.exists(version.score_parts_pdf_key):
                response_data["score_parts_pdf_link"] = request.build_absolute_uri(version.score_parts_pdf_url)
            elif default_storage.exists(version.score_pdf_key):
                response_data["score_pdf_url"] = request.build_absolute_uri(version.score_pdf_url)
                response_data["score_parts_pdf_link"] = request.build_absolute_uri(version.score_pdf_url)

        if version.combined_parts_pdf_key and default_storage.exists(version.combined_parts_pdf_key):
            response_data["combined_parts_pdf_url"] = request.build_absolute_uri(
                version.combined_parts_pdf_url or default_storage.url(version.combined_parts_pdf_key)
            )

        return Response(response_data)

    @action(detail=True, methods=["get"], url_path="download_all_parts")
    def download_all_parts(self, request, pk=None):
        version = self.get_object()

        if not version.combined_parts_pdf_key:
            return Response(
                {"detail": "Combined parts PDF is not available for this version."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not default_storage.exists(version.combined_parts_pdf_key):
            return Response(
                {"detail": "Combined parts PDF file not found in storage."},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_url = version.combined_parts_pdf_url or default_storage.url(version.combined_parts_pdf_key)
        return Response(
            {
                "file_url": request.build_absolute_uri(file_url),
                "redirect": file_url,
            }
        )

    @action(detail=True, methods=["post"])
    def trigger_audio_export(self, request, pk=None):
        version = self.get_object()

        match version.audio_state:
            case ArrangementVersion.AudioStatus.NONE:
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

    @action(detail=True, methods=["get"])
    def list_parts(self, request, pk=None):
        version = self.get_object()

        parts = PartAsset.objects.filter(arrangement_version=version)

        parts_data = []
        for part in parts:
            parts_data.append(
                {
                    "id": part.id,
                    "name": part.name,
                    "is_score": part.is_score,
                    "file_url": request.build_absolute_uri(part.file_url),
                    "download_url": request.build_absolute_uri(
                        f"/api/arrangementversions/{version.id}/download_part/{part.id}/"
                    ),
                }
            )

        return Response(
            {
                "version_id": version.id,
                "parts": parts_data,
                "count": len(parts_data),
            }
        )

    @action(detail=True, methods=["get"], url_path="download_part/(?P<part_id>[^/.]+)")
    def download_part(self, request, pk=None, part_id=None):
        version = self.get_object()

        try:
            part = PartAsset.objects.get(id=part_id, arrangement_version=version)
        except PartAsset.DoesNotExist:
            return Response(
                {"detail": "Part not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not default_storage.exists(part.file_key):
            return Response(
                {"detail": "Part PDF file not found in storage"},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_url = default_storage.url(part.file_key)
        return Response(
            {
                "file_url": request.build_absolute_uri(file_url),
                "redirect": file_url,
            }
        )
