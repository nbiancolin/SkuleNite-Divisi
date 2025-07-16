from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import os

from .tasks import part_formatter_mscz, export_mscz_to_pdf
from .models import UploadSession, ProcessedFile
from .serializers import FormatMsczFileSerializer


class UploadMsczFile(APIView):
    def post(self, request, *args, **kwargs):
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

        os.makedirs(session.mscz_file_location, exist_ok=True)
        os.makedirs(session.output_file_location, exist_ok=True)
        file_path = os.path.join(session.mscz_file_path)
        with open(file_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        return Response(
            {"message": "File Uploaded Successfully", "session_id": session.id},
            status=status.HTTP_200_OK,
        )


class FormatMsczFile(APIView):
    def post(self, request, *args, **kwargs):
        """
        Get style properties, format parts, and return download link.
        """
        serializer = FormatMsczFileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        style = serializer.validated_data["style"]
        show_title = serializer.validated_data["show_title"]
        show_number = serializer.validated_data["show_number"]
        session_id = serializer.validated_data.get("session_id")
        num_measure_per_line = serializer.validated_data["measures_per_line"]

        #Classical is just broadway minus
        if style == "classical":
            style = "broadway"

        if not session_id:
            return Response(
                {"error": "Missing session_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_formatter_mscz(session_id, style, show_title, show_number, num_measure_per_line)

        try:
            d = export_mscz_to_pdf(session_id)
            print(d)
            output_rel_path = d["output"]
        except Exception as e:
            return Response(
                {"error": f"Export failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not os.path.exists(output_rel_path):
            return Response(
                {"error": "Processed file not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        file_url = request.build_absolute_uri(f"/{output_rel_path}")

        return Response(
            {
                "message": "File processed successfully.",
                "score_download_url": file_url,
            },
            status=status.HTTP_200_OK,
        )
