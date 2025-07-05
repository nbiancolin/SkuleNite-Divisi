from rest_framework import serializers
from .models import Ensemble, Arrangement

class EnsembleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ensemble
        fields = ("id", "title", 'arrangements')

class ArrangementSerializer(serializers.ModelSerializer):
    ensemble_name = serializers.CharField(source="ensemble.name", read_only=True)

    class Meta:
        model = Arrangement
        fields = ("id", "title", "act_number", "piece_number", "ensemble", "ensemble_name")