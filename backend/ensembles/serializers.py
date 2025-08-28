from rest_framework import serializers
from .models import Ensemble, Arrangement, ArrangementVersion, Part

VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]


class ArrangementVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrangementVersion
        fields = [
            "id",
            "uuid",
            "version_label",
            "timestamp",
            "is_latest"
        ]


class ArrangementSerializer(serializers.ModelSerializer):
    mvt_no = serializers.ReadOnlyField()
    latest_version = ArrangementVersionSerializer(read_only=True)
    latest_version_num = serializers.ReadOnlyField()

    class Meta:
        model = Arrangement
        fields = [
            "id",
            "ensemble",
            "ensemble_name",
            "ensemble_slug",
            "title",
            "slug",
            "subtitle",
            "composer",
            "act_number",
            "piece_number",
            "mvt_no",
            "style",
            "latest_version",
            "latest_version_num",
        ]
        read_only_fields = [
            "slug",
        ]


class EnsembleSerializer(serializers.ModelSerializer):
    # TODO[Eventually]: Add an "owner" field to say who owns the ensemble

    arrangements = ArrangementSerializer(many=True, read_only=True)

    class Meta:
        model = Ensemble
        fields = ["id", "name", "slug", "arrangements"]
        read_only_fields = ["slug"]


class CreateArrangementVersionMsczSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    arrangement_id = serializers.IntegerField(required=True)
    version_type = serializers.CharField(
        required=True
    )  # TODO: Make this a choice field
    num_measures_per_line_score = serializers.IntegerField(default=8)
    num_measures_per_line_part = serializers.IntegerField(default=6)

    format_parts = serializers.BooleanField(default=True)


class ArrangementVersionDownloadLinksSeiializer(serializers.Serializer):
    version_id = serializers.IntegerField(required=True)
