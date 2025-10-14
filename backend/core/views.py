from rest_framework.views import APIView
from rest_framework.response import Response

from .models import SiteWarning
# Create your views here.

class GetWarningsView(APIView):
    def get(self, request, *args, **kwargs):
        res = SiteWarning.objects.filter(is_visible=True).values_list("text", flat=True)

        return Response(res)