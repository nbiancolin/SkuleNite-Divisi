from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import os

from django.conf import settings

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
        )

        os.makedirs(session.mscz_file_path, exist_ok=True)
        file_path = os.path.join(session.mscz_file_path, uploaded_file.name)
        with open(file_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        return Response(
            {"message": "File Uploaded Successfully", "uuid": session.id},
            status=status.HTTP_200_OK,
        )


class FormatMsczFile(APIView):
    def post(self, request, *args, **kwargs):
        """
        Get style property from request, update model with same UUID, then pass those values in to the part formatter
        """
        serializer = FormatMsczFileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


        style = serializer.validated_data['style']
        show_title = serializer.validated_data['show_title']
        show_number = serializer.validated_data['show_number']
        uuid = request.data.get("uuid")

        # This task takes in the session id, finds the file path, outputs the parts in a different directory
        part_formatter_mscz.call(uuid, style, show_title, show_number)

        # export parts asynchronously, when people call for downloads, block until ready when trying to download
        export_result = export_mscz_to_pdf.delay(uuid)

        if export_result.failed():
            return Response(
                {"error": "export_mscz failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "File processed", "uuid": uuid}, status=status.HTTP_200_OK
        )


# class UploadPartFormatter(APIView):
#     def post(self, request, *args, **kwargs):
#         uploaded_file = request.FILES.get("file")
#         if not uploaded_file:
#             return Response(
#                 {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
#             )

#         session = UploadSession.objects.create(
#             user_agent=request.headers.get("User-Agent"),
#             ip_address=request.META.get("REMOTE_ADDR"),
#         )

#         file_dir = (
#             f"blob/uploads/{session.id}"  # TODO[SC-52] - move to settings.py (the blob)
#         )
#         os.makedirs(file_dir, exist_ok=True)
#         file_path = os.path.join(file_dir, uploaded_file.name)
#         with open(file_path, "wb+") as f:
#             for chunk in uploaded_file.chunks():
#                 f.write(chunk)

#         # Run part_formatter_mscz task synchronously
#         processed_file_path = part_formatter_mscz.call(file_path)

#         # if result.failed():
#         #     return Response(
#         #         {"error": "part_formatter_mscz failed"},
#         #         status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         #     )

#         # Now run export_mscz task
#         export_result = export_mscz_to_pdf.delay(processed_file_path)
#         # export_result.wait()

#         if export_result.failed():
#             return Response(
#                 {"error": "export_mscz failed"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         # Assume export_mscz returns a list of PDF file paths
#         pdf_files = export_result.result if export_result.result else []

#         # Prepare response with PDF files (as URLs or file names)
#         pdf_urls = [
#             os.path.join(settings.MEDIA_URL, os.path.basename(pdf)) for pdf in pdf_files
#         ]

#         return Response(
#             {"message": "File processed", "pdfs": pdf_urls}, status=status.HTTP_200_OK
#         )
