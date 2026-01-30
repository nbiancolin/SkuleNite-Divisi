from rest_framework import serializers

from ensembles.models import EnsembleUsership


from django.contrib.auth import get_user_model


from logging import getLogger
logger = getLogger("EnsembleViews")


VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email"]

class EnsembleUsershipWithUserSerializer(serializers.ModelSerializer):
    
    #SHould use UserSerializer here...
    # user = serializers.

    def save(self, *args, **kwargs):
        raise NotImplementedError("EnsembleUsershipWithUserSerializer is a read only serializer")
    
    class Meta:
        model = EnsembleUsership
        fields = [
            "id",
            "user",
            "role",
            "date_joined"
        ]
        read_only_fields = fields


class EnsembleUsershipSerializer(serializers.ModelSerializer):

    def save(self, *args, **kwargs):
        raise NotImplementedError("EnsembleUsershipSerializer is a read only serializer")

    class Meta:
        model = EnsembleUsership
        fields = [
            "id",
            "user_id",
            "role",
            "date_joined"
        ]
        read_only_fields = fields
