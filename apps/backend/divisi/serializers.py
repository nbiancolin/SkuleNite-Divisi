from rest_framework import serializers
from rest_framework.exceptions import APIException
from ensembles.models import ArrangementVersion

from divisi.models import UploadSession
from divisi.tasks import format_upload_session, export_mscz_to_pdf

STYLE_CHOICES = [("jazz", "Jazz"), ("broadway", "Broadway"), ("classical", "Classical")]


class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSession
        fields = ["id", "created_at", "completed"]


class UploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class FormatMsczFileSerializer(serializers.Serializer):
    default_error_messages = {
        "missing_session": "Session_id field must be provided",
        "invalid_session": "Session id {session_id} does not exist",
    }

    session_id = serializers.UUIDField(required=True)
    style = serializers.ChoiceField(choices=STYLE_CHOICES)
    show_title = serializers.CharField(required=False, default=None)
    show_number = serializers.CharField(required=False, default=None)
    measures_per_line = serializers.IntegerField(required=False, default=None)
    composer = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    arranger = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    version_num = serializers.CharField(required=False, default=None)
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

    def validate_session_id(self, value):
        if not value:
            self.fail("invalid_session")
        if not UploadSession.objects.filter(id=value).exists():
            self.fail("invalid_session", session_id=value)
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
        #TODO[SC-276]: This could be refactored for readability
        assert self.validated_data, "Must call `is_valid` first!"

        style = self.validated_data["style"]
        show_title = self.validated_data["show_title"]
        show_number = self.validated_data["show_number"]
        session_id = self.validated_data["session_id"]
        num_measure_per_line = self.validated_data["measures_per_line"]
        composer = self.validated_data.get("composer")
        arranger = self.validated_data.get("arranger")
        version_num = self.validated_data["version_num"]
        staff_spacing_strategy = self.validated_data["staff_spacing_strategy"]
        staff_spacing_value = self.validated_data["staff_spacing_value"]

        # Classical is just broadway minus show text
        if style == "classical":
            style = "broadway"

        try:
            res = format_upload_session(
                session_id,
                selected_style=style,
                show_title=show_title,
                show_number=show_number,
                num_measures_per_line_part=num_measure_per_line,
                version_num=version_num,
                composer=composer,
                arranger=arranger,
                staff_spacing_strategy=staff_spacing_strategy,
                staff_spacing_value=(
                    str(staff_spacing_value)
                    if staff_spacing_value is not None
                    else None
                ),
            )

            if res["status"] != "success":
                raise Exception(f"Part Formatter Error: {res['details']}")
        except Exception as e:
            raise APIException(detail=f"Part formatter failed: {str(e)}")

        res = export_mscz_to_pdf(session_id)

        if res["status"] != "success":
            raise APIException(detail=f"Export failed: {res.get('details')}")


        # do success stuff
        session = UploadSession.objects.get(id=session_id)
        output_path = res["output"]
        mscz_url = session.output_file_url
        session.completed = True
        session.save()

        return {"output_path": output_path, "mscz_url": mscz_url}
