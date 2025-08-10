from rest_framework import serializers
from .models import Ensemble, Arrangement, ArrangementVersion, Part

VERSION_TYPES = [
    ("major", "Major"),
    ("minor", "Minor"),
    ("patch", 'Patch')
]

class ArrangementSerializer(serializers.ModelSerializer):
    mvt_no = serializers.ReadOnlyField()
    latest_version = serializers.ReadOnlyField()
    latest_version_num = serializers.ReadOnlyField()

    class Meta:
        model = Arrangement
        fields = ['id', 'ensemble', 'title', 'slug', 'subtitle', 'composer', 'act_number', 'piece_number', 'mvt_no', 'latest_version', 'latest_version_num']
        read_only_fields = ['slug', ]


class EnsembleSerializer(serializers.ModelSerializer):
    arrangements = ArrangementSerializer(many=True, read_only=True)

    class Meta:
        model = Ensemble
        fields = ['id', 'name', 'slug', 'arrangements']
        read_only_fields = ['slug']


class ArrangementVersionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ArrangementVersion
        fields = ["id", "arrangement", "version_label", "timestamp",]

class CreateArrangementVersionMsczSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    arrangement_id = serializers.IntegerField(required=True)
    version_type = serializers.CharField(required=True)  #TODO: Make this a choice field


#OLD for now TODO remove
class CreateEnsembleSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    #TODO[Eventually]: Add an "owner" field to say who owns the ensemble

class CreateArrangementSerializer(serializers.Serializer):
    ensemble_name = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    subtitle = serializers.CharField(required=False, default=None)
    composer = serializers.CharField(required=False, default=None)
    arranger = serializers.CharField(required=False, default=None)
    #Thinking here: If not using broadway formatting settings, use show_number to determine order, otherwise use act_number / show_number combo
    act_number = serializers.IntegerField(required=False, default=-1)
    show_number = serializers.IntegerField(required=True)
