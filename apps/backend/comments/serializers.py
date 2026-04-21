from rest_framework import serializers

from comments.models import ArrangementVersionComment, ArrangementVersionCommentThread


class UserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class ArrangementVersionCommentSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = ArrangementVersionComment
        fields = ["id", "author", "body", "created_at", "updated_at"]


class ArrangementVersionCommentThreadSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)
    resolved_by = UserSummarySerializer(read_only=True)
    comments = ArrangementVersionCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ArrangementVersionCommentThread
        fields = [
            "id",
            "arrangement_version",
            "created_by",
            "status",
            "page_number",
            "x",
            "y",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
            "comments",
        ]


class CreateCommentThreadSerializer(serializers.Serializer):
    page_number = serializers.IntegerField(min_value=1)
    x = serializers.FloatField(min_value=0.0, max_value=1.0)
    y = serializers.FloatField(min_value=0.0, max_value=1.0)
    body = serializers.CharField(trim_whitespace=True, min_length=1)


class CreateCommentSerializer(serializers.Serializer):
    body = serializers.CharField(trim_whitespace=True, min_length=1)
