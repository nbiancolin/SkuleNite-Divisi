import io
from rest_framework import serializers
from rest_framework import status

from django.db import transaction
from django.core.files.storage import default_storage

from ensembles.models import Ensemble, Arrangement, ArrangementVersion, Diff
from ensembles.tasks import prep_and_export_mscz, export_arrangement_version, compute_diff

from logging import getLogger

logger = getLogger("EnsembleViews")


VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]


class ArrangementVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrangementVersion
        fields = ["id", "version_label", "timestamp", "is_latest"]


class ArrangementSerializer(serializers.ModelSerializer):
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
            "mvt_no",
            "style",
            "latest_version",
            "latest_version_num",
        ]
        read_only_fields = [
            "slug",
            "ensemble_name",
            "ensemble_slug",
        ]


class EnsembleSerializer(serializers.ModelSerializer):
    # TODO[Eventually]: Add an "owner" field to say who owns the ensemble

    arrangements = ArrangementSerializer(many=True, read_only=True)

    class Meta:
        model = Ensemble
        fields = ["id", "name", "slug", "arrangements"]
        read_only_fields = ["slug"]


class CreateArrangementVersionMsczSerializer(serializers.Serializer):
    default_error_messages = {
        "invalid_version_type": "Version type not one of 'major', 'minor', 'patch'",
        "invalid_arr_id": "Arrangement with id {id} does not exist",
    }

    file = serializers.FileField(allow_empty_file=False)
    arrangement_id = serializers.IntegerField(required=True)
    version_type = serializers.CharField(required=True)
    num_measures_per_line_score = serializers.IntegerField(default=8)
    num_measures_per_line_part = serializers.IntegerField(default=6)
    num_lines_per_page = serializers.IntegerField(default=8)

    format_parts = serializers.BooleanField(default=True)

    def validate_version_type(self, value):
        if value not in [t[0] for t in VERSION_TYPES]:
            self.fail("invalid_version_type")
        return value

    def validate_arrangement_id(self, value):
        if not Arrangement.objects.filter(id=value).exists():
            self.fail("invalid_arr_id", id=value)
        return value

    def save(self, **kwargs):
        assert self.validated_data, "Must call is_valid first!"
        with transaction.atomic():
            version = ArrangementVersion.objects.create(
                arrangement=Arrangement.objects.get(
                    id=self.validated_data["arrangement_id"]
                ),
                file_name=self.validated_data["file"].name,
                num_measures_per_line_score=self.validated_data[
                    "num_measures_per_line_score"
                ],
                num_measures_per_line_part=self.validated_data[
                    "num_measures_per_line_part"
                ],
                num_lines_per_page=self.validated_data["num_lines_per_page"],
            )

            version.save(
                version_type=self.validated_data["version_type"],
            )

        uploaded_file = self.validated_data["file"]

        # Save file to storage using the storage key
        try:
            # Create a file-like object from the uploaded file
            file_content = b""
            for chunk in uploaded_file.chunks():
                file_content += chunk

            # Save to storage using the key
            default_storage.save(version.mscz_file_key, io.BytesIO(file_content))
            logger.info(f"Saved file to storage: {version.mscz_file_key}")

        except Exception as e:
            logger.error(f"Failed to save file to storage: {e}")
            # Clean up the version if file save failed
            version.delete()
            return {"error": "Failed to save file to storage"}

        # Format mscz if selected by FE
        if self.validated_data.get("format_parts", None):
            prep_and_export_mscz.delay(version.pk)
        else:
            # Just export
            export_arrangement_version.delay(version.pk)

        # epxort MXL for diff calculation
        export_arrangement_version(version.pk, action="mxl")

        return {"success": True, "version_id": version.id}


class DiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diff
        fields = "__all__"


class ComputeDiffSerializer(serializers.Serializer):
    from_version_id = serializers.IntegerField(required=False)
    to_version_id = serializers.IntegerField(required=False)
    diff_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        diff_id = attrs.get("diff_id")
        from_version_id = attrs.get("from_version_id")
        to_version_id = attrs.get("to_version_id")

        if not diff_id and not (from_version_id and to_version_id):
            raise serializers.ValidationError(
                "Must either pass in diff_id or (from_version_id and to_version_id)"
            )

        if diff_id:
            try:
                Diff.objects.get(id=diff_id)
            except Diff.DoesNotExist:
                raise serializers.ValidationError(
                    "Diff_id does not match any diffs in the database."
                )
        elif from_version_id and to_version_id:
            try:
                from_version = ArrangementVersion.objects.get(id=from_version_id)
                to_version = ArrangementVersion.objects.get(id=to_version_id)
            except ArrangementVersion.DoesNotExist:
                raise serializers.ValidationError(
                    "Invalid from_version_id or to_version_id provided."
                )

            if from_version.arrangement != to_version.arrangement:
                raise serializers.ValidationError(
                    "ArrangementVersions must be from the same arrangement."
                )

        return attrs

    def save(self, **kwargs):
        """Compute actual diff"""
        diff_id = self.validated_data.get("diff_id")
        if diff_id:
            diff = Diff.objects.get(id=diff_id)
            if diff.status == "failed":
                created = True
                diff.status = "pending"
            else:
                created = False
        else:
            if kwargs.get("get"):
                from_version_id = self.validated_data.get("from_version_id")
                to_version_id = self.validated_data.get("to_version_id")
                try:
                    diff = Diff.objects.get(
                        from_version=ArrangementVersion.objects.get(id=from_version_id),
                        to_version=ArrangementVersion.objects.get(id=to_version_id),
                        file_name="comp-diff.pdf",
                    )
                    created = False
                except Diff.DoesNotExist:
                    return {"error_msg": "cannot create diff on get request"}
            else:
                from_version_id = self.validated_data.get("from_version_id")
                to_version_id = self.validated_data.get("to_version_id")
                diff, created = Diff.objects.get_or_create(
                    from_version=ArrangementVersion.objects.get(id=from_version_id),
                    to_version=ArrangementVersion.objects.get(id=to_version_id),
                    file_name="comp-diff.pdf",
                )

            if created:
                compute_diff.delay(diff.id)
        diff.refresh_from_db()
        return {
            "id": diff.id,
            "status": diff.status,
            "file_url": diff.file_url,
            "error_msg": diff.error_msg,
        }
