import io
from logging import getLogger

from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from ensembles.formatting_steps_constants import (
    FORMATTING_STEP_KEYS,
    default_formatting_steps,
    merge_formatting_step_defaults,
)
from ensembles.models import (
    Arrangement,
    ArrangementVersion,
    Commit,
)
from ensembles.tasks import (
    apply_metadata_and_export_mscz,
    prep_and_export_mscz,
)

logger = getLogger("arrangement_version_serializer")


VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]

def coerce_formatting_steps(raw) -> dict[str, bool]:
    """Merge client partial dict with defaults; reject unknown keys and non-bool values."""
    base = default_formatting_steps()
    if raw is None:
        return base
    if not isinstance(raw, dict):
        raise serializers.ValidationError("formatting_steps must be a JSON object.")
    unknown = set(raw) - set(FORMATTING_STEP_KEYS)
    if unknown:
        raise serializers.ValidationError(
            f"Unknown formatting_steps keys: {sorted(unknown)}"
        )
    for k in FORMATTING_STEP_KEYS:
        if k in raw:
            v = raw[k]
            if not isinstance(v, bool):
                raise serializers.ValidationError(
                    {k: "Each formatting_steps value must be a boolean."}
                )
            base[k] = v
    merge_formatting_step_defaults(base)
    return base


class FormattingStepsField(serializers.Field):
    """Accepts a dict (JSON body) or JSON string (multipart form)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        import json

        if data in (None, "", serializers.empty):
            return None
        if isinstance(data, dict):
            return coerce_formatting_steps(data)
        if isinstance(data, (bytes, bytearray)):
            data = data.decode()
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(
                    "formatting_steps must be valid JSON."
                ) from e
            return coerce_formatting_steps(parsed)
        raise serializers.ValidationError(
            "formatting_steps must be an object or JSON string."
        )

class ArrangementVersionSerializer(serializers.ModelSerializer):
    audio_state = serializers.CharField(
        source="get_audio_state_display", read_only=True
    )

    class Meta:
        model = ArrangementVersion
        fields = ["id", "version_label", "timestamp", "is_latest", "audio_state"]


class CreateArrangementVersionFromCommitSerializer(serializers.Serializer):
    default_error_messages = {
        "invalid_version_type": "Version type not one of 'major', 'minor', 'patch'",
        "invalid_arr_id": "Arrangement with id {id} does not exist",
    }

    commit_id = serializers.IntegerField(required=True)
    version_type = serializers.CharField(required=True)

    num_measures_per_line_score = serializers.IntegerField(default=8)
    num_measures_per_line_part = serializers.IntegerField(default=6)
    num_lines_per_page = serializers.IntegerField(default=8)

    staff_spacing_strategy = serializers.ChoiceField(
        choices=ArrangementVersion.StaffSpacingStrategy.choices,
        default="predict",
        required=False,
    )
    staff_spacing_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=5,
        required=False,
        allow_null=True,
    )

    format_parts = serializers.BooleanField(default=True)
    formatting_steps = FormattingStepsField(required=False, allow_null=True)

    def validate_version_type(self, value):
        if value not in [t[0] for t in VERSION_TYPES]:
            self.fail("invalid_version_type")
        return value

    def validate_commit_id(self, value):
        if not Commit.objects.filter(id=value).exists():
            self.fail("invalid_commit_id", value)
        return value

    def validate(self, attrs):
        strategy = attrs.get("staff_spacing_strategy", "predict")
        val = attrs.get("staff_spacing_value")
        if strategy != "override":
            attrs["staff_spacing_value"] = None
        elif val is None:
            raise serializers.ValidationError(
                {
                    "staff_spacing_value": "Required when staff_spacing_strategy is override."
                }
            )
        return attrs

    def save(self, **kwargs):
        assert self.validated_data, "Must call is_valid first!"

        commit = Commit.objects.get(id=self.validated_data["commit_id"])

        with transaction.atomic():
            fs = self.validated_data.get("formatting_steps")
            version = ArrangementVersion.objects.create(
                arrangement=Arrangement.objects.get(id=commit.arrangement_id),
                file_name=commit.file_name,
                num_measures_per_line_score=self.validated_data[
                    "num_measures_per_line_score"
                ],
                num_measures_per_line_part=self.validated_data[
                    "num_measures_per_line_part"
                ],
                num_lines_per_page=self.validated_data["num_lines_per_page"],
                staff_spacing_strategy=self.validated_data["staff_spacing_strategy"],
                staff_spacing_value=self.validated_data["staff_spacing_value"],
                formatting_steps=(fs if fs is not None else default_formatting_steps()),
            )

            version.save(
                version_type=self.validated_data["version_type"],
            )

            commit.version_id = version.id
            commit.save(update_fields=["version_id"])

        # copy file from commit to version
        with default_storage.open(commit.mscz_file_key) as f:
            default_storage.save(version.mscz_file_key, f)

        # Format mscz if selected by FE; otherwise still stamp version metadata before export
        if self.validated_data.get("format_parts", None):
            prep_and_export_mscz.delay(version.pk)
        else:
            apply_metadata_and_export_mscz.delay(version.pk)

        # epxort MXL for diff calculation (unnecessary)
        # export_arrangement_version(version.pk, action="mxl")

        return {"success": True, "version_id": version.id}


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

    staff_spacing_strategy = serializers.ChoiceField(
        choices=ArrangementVersion.StaffSpacingStrategy.choices,
        default="predict",
        required=False,
    )
    staff_spacing_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=5,
        required=False,
        allow_null=True,
    )

    format_parts = serializers.BooleanField(default=True)
    formatting_steps = FormattingStepsField(required=False, allow_null=True)

    def validate_version_type(self, value):
        if value not in [t[0] for t in VERSION_TYPES]:
            self.fail("invalid_version_type")
        return value

    def validate_arrangement_id(self, value):
        if not Arrangement.objects.filter(id=value).exists():
            self.fail("invalid_arr_id", id=value)
        return value

    def validate(self, attrs):
        strategy = attrs.get("staff_spacing_strategy", "predict")
        val = attrs.get("staff_spacing_value")
        if strategy != "override":
            attrs["staff_spacing_value"] = None
        elif val is None:
            raise serializers.ValidationError(
                {
                    "staff_spacing_value": "Required when staff_spacing_strategy is override."
                }
            )
        return attrs

    def save(self, **kwargs):
        assert self.validated_data, "Must call is_valid first!"
        with transaction.atomic():
            fs = self.validated_data.get("formatting_steps")
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
                staff_spacing_strategy=self.validated_data["staff_spacing_strategy"],
                staff_spacing_value=self.validated_data["staff_spacing_value"],
                formatting_steps=(fs if fs is not None else default_formatting_steps()),
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

        # Format mscz if selected by FE; otherwise still stamp version metadata before export
        if self.validated_data.get("format_parts", None):
            prep_and_export_mscz.delay(version.pk)
        else:
            apply_metadata_and_export_mscz.delay(version.pk)

        # epxort MXL for diff calculation (unnecessary)
        # export_arrangement_version(version.pk, action="mxl")

        return {"success": True, "version_id": version.id}