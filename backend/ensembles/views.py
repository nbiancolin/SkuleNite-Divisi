from rest_framework import viewsets
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import CreateEnsembleSerializer, CreateArrangementSerializer


class CreateEnsembleView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = CreateEnsembleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        ens = Ensemble.objects.create(name=serializer.validated_data["name"])

        return Response(
            {"message": "Ensemble Created Successfully", "sanitized_name": ens.sanitized_name},
            status=status.HTTP_200_OK,
        )

\
    
