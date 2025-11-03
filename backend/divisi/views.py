from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.files.storage import default_storage

from divisi.models import UploadSession
from divisi.serializers import FormatMsczFileSerializer

import logging

logger = logging.getLogger("PartFormatter")


class UploadMsczFile(APIView):
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create a session first
        session = UploadSession.objects.create(
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.META.get("REMOTE_ADDR"),
            file_name=uploaded_file.name,
        )

        key = session.mscz_file_key

        # Save the uploaded file to the storage backend
        default_storage.save(key, uploaded_file)

        file_url = default_storage.url(key)

        return Response(
            {
                "message": "File uploaded successfully",
                "session_id": session.id,
                "file_url": file_url,
            },
            status=status.HTTP_200_OK,
        )


class FormatMsczFile(APIView):
    def post(self, request, *args, **kwargs):
        """
        Get style properties, format parts, and return download link.
        """
        serializer = FormatMsczFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        output_path, mscz_url = serializer.save()

        return Response(
            {
                "message": "File processed successfully.",
                "score_download_url": request.build_absolute_uri(output_path),
                "mscz_download_url": request.build_absolute_uri(mscz_url),
            },
            status=status.HTTP_200_OK,
        )
