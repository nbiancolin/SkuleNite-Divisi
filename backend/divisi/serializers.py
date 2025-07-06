from rest_framework import serializers
from .models import Ensemble, Arrangement


class ArrangementSerializer(serializers.ModelSerializer):
    ensemble_name = serializers.CharField(source="ensemble.name", read_only=True)

    class Meta:
        model = Arrangement
        fields = ["id", "ensemble_name", "title", "subtitle", "mvt_no"]


class EnsembleSerializer(serializers.ModelSerializer):
    arrangements = ArrangementSerializer(many=True, read_only=True)

    class Meta:
        model = Ensemble
        fields = ("id", "name", "arrangements")


class ArrangementReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Arrangement
        fields = ["id", "title", "subtitle", "act_number", "piece_number"]


class EnsembleDetailSerializer(serializers.ModelSerializer):
    arrangements = ArrangementReadSerializer(many=True, read_only=True)

    class Meta:
        model = Ensemble
        fields = ["id", "title", "arrangements"]
