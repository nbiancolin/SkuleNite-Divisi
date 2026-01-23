from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.core.files.storage import default_storage

from divisi.models import UploadSession
from divisi.serializers import FormatMsczFileSerializer

import logging

logger = logging.getLogger("Divisi-Views")


class PartFormatterViewSet(viewsets.ViewSet):
    """
    ViewSet for part formatter endpoints.
    These endpoints do not require authentication or CSRF tokens.
    """
    permission_classes = [AllowAny]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to exempt CSRF protection.
        """
        return super().dispatch(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def upload_mscz(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        session = UploadSession.objects.create(
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.META.get("REMOTE_ADDR"),
            file_name=uploaded_file.name,
        )

        key = session.mscz_file_key
        default_storage.save(key, uploaded_file)
        file_url = default_storage.url(key)

        #TODO: Have it extract the title from the file and display it on the FE
        #update Jan 6 - Part formatter can extract the title from the file, just need to process it and tell it to do that

        return Response(
            {
                "message": "File uploaded successfully",
                "session_id": session.id,
                "file_url": file_url,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def format_mscz(self, request):
        """
        Get style properties, format parts, and return download link.
        """
        serializer = FormatMsczFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = serializer.save()

        return Response(
            {
                "message": "File processed successfully.",
                "score_download_url": request.build_absolute_uri(res["output_path"]),
                "mscz_download_url": request.build_absolute_uri(res["mscz_url"]),
            },
            status=status.HTTP_200_OK,
        )
