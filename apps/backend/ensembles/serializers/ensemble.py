from collections import defaultdict

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers

from ensembles.models import (
    Ensemble,
    EnsembleUsership,
    PartAsset,
    PartBook,
    PartName,
    EnsembleTemplate,
)
from ensembles.serializers.arrangement import ArrangementSerializer

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
            "has_template"
        ]
        read_only_fields = ["slug", "join_link", "is_admin", "userships"]

    def _get_request_user_usership(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        prefetched_userships = getattr(obj, "_prefetched_objects_cache", {}).get(
            "userships"
        )
        if prefetched_userships is None:
            return EnsembleUsership.objects.filter(
                ensemble=obj, user=request.user
            ).first()

        for usership in prefetched_userships:
            if usership.user_id == request.user.id:
                return usership
        return None

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if obj.owner_id == request.user.id:
                return True
            ship = self._get_request_user_usership(obj)
            return ship is not None and ship.role == EnsembleUsership.Role.ADMIN
        return False

    def get_join_link(self, obj):
        """Generate join link if user is owner or admin"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Check if user is owner
            if obj.owner == request.user:
                token = obj.get_or_create_invite_token()
                frontend_url = getattr(
                    settings, "FRONTEND_URL", "http://localhost:5173"
                )
                return f"{frontend_url.rstrip('/')}/join/{token}"

            # Check if user has admin role
            ship = self._get_request_user_usership(obj)
            if ship is not None and ship.role == EnsembleUsership.Role.ADMIN:
                token = obj.get_or_create_invite_token()
                frontend_url = getattr(
                    settings, "FRONTEND_URL", "http://localhost:5173"
                )
                return f"{frontend_url.rstrip('/')}/join/{token}"

            return None
        return None

    def get_userships(self, obj):
        """Get userships details"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            userships = getattr(obj, "_prefetched_objects_cache", {}).get("userships")
            if userships is None:
                userships = EnsembleUsership.objects.filter(
                    ensemble=obj
                ).select_related("user")
            return [
                # TODO[SC-278]: Usership serializer
                {
                    "id": usership.id,
                    "user": UserSerializer(usership.user).data,
                    "role": usership.role,
                    "date_joined": usership.date_joined,
                }
                for usership in userships
            ]
        return None

    def get_part_names(self, obj):
        """get part names details"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            from ensembles.lib.part_name_matrix import (
                part_names_with_latest_part_assets,
            )

            parts = part_names_with_latest_part_assets(obj)
            part_name_ids = [part.id for part in parts]

            arrangement_titles_by_part_name_id = defaultdict(list)
            arrangement_ids_by_part_name_id = defaultdict(list)
            if part_name_ids:
                part_assets = (
                    PartAsset.objects.filter(
                        part_name_id__in=part_name_ids,
                        arrangement_version__arrangement__ensemble=obj,
                        arrangement_version__is_latest=True,
                        is_score=False,
                    )
                    .select_related("arrangement_version__arrangement")
                    .order_by(
                        "arrangement_version__arrangement__mvt_no",
                        "arrangement_version__arrangement__id",
                    )
                )
                for asset in part_assets:
                    arr = asset.arrangement_version.arrangement
                    arrangement_titles_by_part_name_id[asset.part_name_id].append(
                        arr.title
                    )
                    arrangement_ids_by_part_name_id[asset.part_name_id].append(arr.id)

            # Keep a stable, typed shape for the frontend
            return [
                {
                    "id": part.id,
                    "display_name": part.display_name,
                    "arrangements": arrangement_titles_by_part_name_id.get(part.id, []),
                    "arrangement_ids": arrangement_ids_by_part_name_id.get(part.id, []),
                    "order": part.order,
                }
                for part in parts
            ]

    def get_part_books(self, obj):
        """List part books for this ensemble (all parts, all revisions) with download URLs when rendered."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []
        books = getattr(obj, "_prefetched_objects_cache", {}).get("part_books")
        if books is None:
            books = (
                PartBook.objects.filter(ensemble=obj)
                .select_related("part_name")
                .order_by("part_name__display_name", "-revision")
            )
        result = []
        for book in books:
            item = {
                "id": book.id,
                "part_name_id": book.part_name_id,
                "part_display_name": book.part_name.display_name,
                "revision": book.revision,
                "created_at": book.created_at.isoformat() if book.created_at else None,
                "finalized_at": book.finalized_at.isoformat()
                if book.finalized_at
                else None,
                "is_rendered": book.is_rendered,
                "download_url": None,
            }
            # Avoid a storage existence check on list endpoints; this can be slow on remote storage.
            if book.is_rendered:
                file_url = default_storage.url(book.pdf_file_key)
                item["download_url"] = request.build_absolute_uri(file_url)
            result.append(item)
        return result


class EnsembleListSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField(read_only=True)
    arrangements_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Ensemble
        fields = [
            "id",
            "name",
            "slug",
            "is_admin",
            "arrangements_count",
            "part_books_generating",
            "latest_part_book_revision",
        ]
        read_only_fields = fields

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.owner_id == request.user.id:
            return True
        prefetched_userships = getattr(obj, "_prefetched_objects_cache", {}).get(
            "userships"
        )
        if prefetched_userships is not None:
            for usership in prefetched_userships:
                if (
                    usership.user_id == request.user.id
                    and usership.role == EnsembleUsership.Role.ADMIN
                ):
                    return True
            return False
        return EnsembleUsership.objects.filter(
            ensemble=obj, user=request.user, role=EnsembleUsership.Role.ADMIN
        ).exists()

    def get_arrangements_count(self, obj):
        annotated_count = getattr(obj, "arrangements_count", None)
        if annotated_count is not None:
            return annotated_count
        return obj.arrangements.count()


class EnsemblePartNameRenameSerializer(serializers.Serializer):
    part_name_id = serializers.IntegerField(required=True)
    display_name = serializers.CharField(required=True, max_length=64)

    def validate(self, attrs):
        ensemble = self.context["ensemble"]
        try:
            part = PartName.objects.get(id=attrs["part_name_id"], ensemble=ensemble)
        except PartName.DoesNotExist:
            raise serializers.ValidationError(
                {"part_name_id": "Invalid part name for this ensemble."}
            )

        attrs["part"] = part
        return attrs


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
            raise serializers.ValidationError("Cannot merge a PartName with itself.")

        # Stash for use in the view to avoid re-querying
        attrs["first_part"] = first_part
        attrs["second_part"] = second_part

        return attrs
    
class UploadEnsembleTemplateSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)


    def save(self, **kwargs):
        ensemble = self.context["ensemble"]

        
        if ensemble.has_template:
            ensemble.template.is_latest=False

        EnsembleTemplate.objects.create(ensemble=ensemble, is_latest=True)
