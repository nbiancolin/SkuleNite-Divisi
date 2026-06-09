from rest_framework import serializers

from ensembles.models import (
    Commit,
)
from users.serializers import UserSerializer


class CommitSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Commit
        fields = [
            "id",
            "arrangement_id",
            "timestamp",
            "message",
            "has_version",
            "created_by",
            "is_merge_conflict",
        ]