from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import os

from django.conf import settings

from .tasks import part_formatter_mscz, export_mscz_to_pdf


class UploadPartFormatter(APIView):

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_dir = "blob/in_progress/"
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, uploaded_file.name)
        with open(file_path, "wb+") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Run part_formatter_mscz task synchronously
        result = part_formatter_mscz.apply_async(args=[file_path])
        result.wait()  # Wait for task to finish

        if result.failed():
            return Response({"error": "part_formatter_mscz failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Now run export_mscz task
        export_result = export_mscz_to_pdf.apply_async(args=[file_path])
        export_result.wait()

        if export_result.failed():
            return Response({"error": "export_mscz failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Assume export_mscz returns a list of PDF file paths
        pdf_files = export_result.result if export_result.result else []

        # Prepare response with PDF files (as URLs or file names)
        pdf_urls = [os.path.join(settings.MEDIA_URL, os.path.basename(pdf)) for pdf in pdf_files]

        return Response({"message": "File processed", "pdfs": pdf_urls}, status=status.HTTP_200_OK)
    
