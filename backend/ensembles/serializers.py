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
    from_version_id = serializers.IntegerField(required=False)
    to_version_id = serializers.IntegerField(required=False)
    diff_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get("diff_id") or not (attrs.get("from_version_id") and attrs.get("to_version_id")):
            raise serializers.ValidationError("Must either pass in diff_id or (from_version_id and to_version_id)")
        if attrs.get("diff_id"):
            try:
                Diff.objects.get(id=attrs.get("diff_id"))
            except Diff.DoesNotExist:
                raise serializers.ValidationError("Diff_id does not match any diffs in DB must be from the same arrangement")
        if ArrangementVersion.objects.get(id=attrs["from_version_id"]).arrangement != ArrangementVersion.objects.get(id=attrs["to_version_id"]).arrangement:
            raise serializers.ValidationError("ArrangementVersions must be from the same arrangement")
            return False
        return attrs


    def save(self, **kwargs):
        """Compute actual diff"""
        if self.diff_id:
            diff = Diff.objects.get(id=self.diff_id)
        else:
            Diff.objects.get(
                from_version=self.from_version_id,
                to_version=self.to_version_id,
            )

        if kwargs.get("get"):
            
            return serializers.serialize(diff)
        else:
            diff, created = Diff.objects.get_or_create(
                from_version=self.from_version_id,
                to_version=self.to_version_id,
                file_name="comp-diff.pdf",
            )

            if created:
                compute_diff.delay(diff.id)
            diff.refresh_from_db()
            return serializers.serialize(diff)
            

