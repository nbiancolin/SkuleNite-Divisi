from django.shortcuts import render
from rest_framework import viewsets

from .serializers import EnsembleSerializer, ArrangementSerializer
from .models import Ensemble, Arrangement

class EnsembleView(viewsets.ModelViewSet):
    serializer_class = EnsembleSerializer
    queryset = Ensemble.objects.all()

class ArrangementView(viewsets.ModelViewSet):
    serializer_class = ArrangementSerializer

    def get_queryset(self):
        queryset = Arrangement.objects.all()
        ensemble_id = self.request.query_params.get("ensemble")

        if ensemble_id:
            try:
                queryset = queryset.filter(ensemble_id=int(ensemble_id))
            except ValueError:
                print("Invalid ensemble ID:", ensemble_id)

        return queryset