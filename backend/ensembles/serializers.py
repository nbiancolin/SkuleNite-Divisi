from rest_framework import serializers
from .models import Ensemble, Arrangement, ArrangementVersion, Diff

from .tasks import compute_diff

from django.db.utils import IntegrityError

VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]


class ArrangementVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrangementVersion
        fields = ["id", "version_label", "timestamp", "is_latest"]


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


class ComputeDiffSerializer(serializers.Serializer):
    from_version_id = serializers.IntegerField(required=True)
    to_version_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if ArrangementVersion.objects.get(id=attrs["from_version_id"]).arrangement != ArrangementVersion.objects.get(id=attrs["to_version_id"]).arrangement:
            raise serializers.ValidationError("ArrangementVersions must be from the same arrangement")
        if Diff.objects.get(from_version__id=attrs["from_version_id"], to_version__id=attrs["to_version_id"]):
            raise serializers.ValidationError("Diff already exists")
        return attrs

        

    def save(self, **kwargs):
        """Compute actual diff"""
        d = Diff.objects.create(
            from_version=self.from_version_id,
            to_version=self.to_version_id,
            file_name="comp-diff.pdf",
        )


        res = compute_diff.delay(d.id)
        assert res["status"] == "success"
        return d
            

