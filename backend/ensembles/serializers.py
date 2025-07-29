from rest_framework import serializers
from .models import Ensemble, Arrangement, ArrangementVersion, Part


class CreateEnsembleSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    #TODO[Eventually]: Add an "owner" field to say who owns the ensemble

class CreateArrangementSerializer(serializers.Serializer):
    ensemble_id = serializers.UUIDField()
    title = serializers.CharField(required=True)
    subtitle = serializers.CharField(required=False, default=None)
    composer = serializers.CharField(required=False, default=None)
    arranger = serializers.CharField(required=False, default=None)
    #Thinking here: If not using broadway formatting settings, use show_number to determine order, otherwise use act_number / show_number combo
    act_number = serializers.IntegerField(required=False, default=0)
    show_number = serializers.IntegerField(required=True)

#TODO: Write MsczUpload Serializer