from rest_framework import viewsets
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from .models import Arrangement, Ensemble, ArrangementVersion
from .serializers import ArrangementSerializer, EnsembleSerializer, ArrangementVersionSerializer, UploadPartsSerializer
from logging import getLogger

logger = getLogger("EnsembleViews")


class EnsembleViewSet(viewsets.ModelViewSet):
    serializer_class = EnsembleSerializer
    queryset = Ensemble.objects.all()


class ArrangementViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementSerializer

    def get_queryset(self):
        queryset = Arrangement.objects.all()
        ensemble_id = self.request.query_params.get("ensemble")
        arrangement_id = self.request.query_params.get("id")
        if arrangement_id:
            try:
                queryset = queryset.filter(id=int(arrangement_id))
            except ValueError:
                logger.warning("Invalid arrangement ID:", ensemble_id)

        if ensemble_id:
            try:
                queryset = queryset.filter(ensemble_id=int(ensemble_id))
            except ValueError:
                logger.warning("Invalid ensemble ID:", ensemble_id)

        return queryset


class ArrangementVersionCreateView(CreateAPIView):
    queryset = ArrangementVersion.objects.all()
    serializer_class = ArrangementVersionSerializer


class UploadArrangementPartsView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = UploadPartsSerializer(data=request.data)
        if serializer.is_valid():
            parts = serializer.save()
            return Response({'message': f'{len(parts)} parts uploaded'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
