from rest_framework import serializers
from .models import Ensemble, Arrangement, ArrangementVersion, Part


class ArrangementSerializer(serializers.ModelSerializer):
    ensemble_name = serializers.CharField(source="ensemble.name", read_only=True)

    class Meta:
        model = Arrangement
        fields = ["id", "ensemble_name", "title", "subtitle", "mvt_no", "latest"]


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


class ArrangementVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrangementVersion
        fields = '__all__'

class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = ['part_name', 'file']

class UploadPartsSerializer(serializers.Serializer):
    arrangement_id = serializers.IntegerField()
    version_type = serializers.ChoiceField(choices=["major", "minor", "patch"])
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )

    def create(self, validated_data):
        arrangement = Arrangement.objects.get(id=validated_data['arrangement_id'])

        # Create a new ArrangementVersion and bump version label
        version = ArrangementVersion(arrangement=arrangement)
        version.save(version_type=validated_data['version_type'])

        parts = []
        for f in validated_data['files']:
            part = Part.objects.create(
                version=version,
                part_name=f.name.replace('.pdf', ''),
                file=f
            )
            parts.append(part)

        return parts