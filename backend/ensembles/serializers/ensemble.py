from rest_framework import serializers

from django.core.files.storage import default_storage
from django.conf import settings

from ensembles.models import Ensemble, EnsembleUsership, PartBook, PartName
from ensembles.serializers.arrangement import ArrangementSerializer
from ensembles.serializers.ensemble_usership import EnsembleUsershipSerializer

from logging import getLogger

logger = getLogger("EnsembleViews")


VERSION_TYPES = [("major", "Major"), ("minor", "Minor"), ("patch", "Patch")]


class EnsembleSerializer(serializers.ModelSerializer):
    arrangements = ArrangementSerializer(many=True, read_only=True)
    join_link = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField(read_only=True)
    userships = serializers.SerializerMethodField(read_only=True)
    part_names = serializers.SerializerMethodField(read_only=True)
    part_books = serializers.SerializerMethodField(read_only=True)
    default_style = serializers.CharField(required=True)

    class Meta:
        model = Ensemble
        fields = [
            "id",
            "name",
            "slug",
            "arrangements",
            "join_link",
            "is_admin",
            "userships",
            "part_names",
            "part_books_generating",
            "latest_part_book_revision",
            "part_books",
            "default_style",
        ]
        read_only_fields = ["slug", "join_link", "is_admin", "userships"]

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.is_ensemble_admin(obj)

    def get_join_link(self, obj):
        """Generate join link if user is owner or admin"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Check if user is owner
            if obj.owner == request.user:
                token = obj.get_or_create_invite_token()
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                return f"{frontend_url.rstrip('/')}/join/{token}"
            
            # Check if user has admin role
            try:
                ship = EnsembleUsership.objects.get(ensemble=obj, user=request.user)
                if ship.role == EnsembleUsership.Role.ADMIN:
                    token = obj.get_or_create_invite_token()
                    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                    return f"{frontend_url.rstrip('/')}/join/{token}"
            except EnsembleUsership.DoesNotExist:
                pass

            return None
        return None

    def get_userships(self, obj):
        """Get userships details"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return [
                EnsembleUsershipSerializer(usership).data
                for usership in EnsembleUsership.objects.filter(ensemble=obj)
            ]
        return None


    def get_part_names(self, obj):
        """get part names details"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Keep a stable, typed shape for the frontend
            return [
                {"id": part.id, "display_name": part.display_name}
                for part in obj.part_names.all()
            ]

    def get_part_books(self, obj):
        """List part books for this ensemble (all parts, all revisions) with download URLs when rendered."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []
        books = (
            PartBook.objects.filter(ensemble=obj)
            .select_related("part_name")
            .order_by("part_name__display_name", "-revision")
        )
        result = []
        for book in books:
            #TODO[SC-278]: Serializer
            item = {
                "id": book.id,
                "part_name_id": book.part_name_id,
                "part_display_name": book.part_name.display_name,
                "revision": book.revision,
                "created_at": book.created_at.isoformat() if book.created_at else None,
                "finalized_at": book.finalized_at.isoformat() if book.finalized_at else None,
                "is_rendered": book.is_rendered,
                "download_url": None,
            }
            if book.is_rendered and default_storage.exists(book.pdf_file_key):
                file_url = default_storage.url(book.pdf_file_key)
                item["download_url"] = request.build_absolute_uri(file_url)
            result.append(item)
        return result
    


class EnsemblePartNameMergeSerializer(serializers.Serializer):
    default_error_messages = {
        "invalid_part_id": "One or both of these part ids is incorrect."
    }
    first_id = serializers.IntegerField(required=True)
    second_id = serializers.IntegerField(required=True)

    new_displayname = serializers.CharField(required=False)

    def validate(self, attrs):
        ensemble = self.context["ensemble"]
        first_id = attrs["first_id"]
        second_id = attrs["second_id"]

        try:
            first_part = PartName.objects.get(id=first_id)
            second_part = PartName.objects.get(id=second_id)
        except PartName.DoesNotExist:
            self.fail("invalid_part_id")

        if first_part.ensemble_id != second_part.ensemble_id:
            self.fail("invalid_part_id")

        if ensemble.id != first_part.ensemble_id:
            self.fail("invalid_part_id")

        # prevent merging the same row into itself
        if first_part.id == second_part.id:
            raise serializers.ValidationError(
                "Cannot merge a PartName with itself."
            )

        # Stash for use in the view to avoid re-querying
        attrs["first_part"] = first_part
        attrs["second_part"] = second_part

        return attrs
