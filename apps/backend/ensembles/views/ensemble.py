from comments.models import ArrangementVersionCommentThread
from django.conf import settings
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.db.models.expressions import RawSQL
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ensembles.lib.part_name_matrix import build_part_name_matrix
from ensembles.models import (
    Arrangement,
    ArrangementVersion,
    Commit,
    Ensemble,
    EnsembleUsership,
    PartBook,
    PartName,
)
from ensembles.models.constants import PART_BOOK_LAYOUT_CHOICES
from ensembles.serializers import (
    ArrangementSerializer,
    EnsembleListSerializer,
    EnsemblePartNameMergeSerializer,
    EnsemblePartNameRenameSerializer,
    EnsembleSerializer,
)
from ensembles.tasks.part_books import (
    VALID_LAYOUTS,
    generate_books_for_ensemble,
    generate_part_book,
)


class EnsembleViewSet(viewsets.ModelViewSet):
    serializer_class = EnsembleSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return EnsembleListSerializer
        return EnsembleSerializer

    def get_queryset(self):
        """Filter ensembles to only those the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return Ensemble.objects.none()

        base_qs = Ensemble.objects.filter(
            Q(owner=user) | Q(userships__user=user)
        ).select_related("owner")

        if self.action == "list":
            return (
                base_qs.annotate(
                    arrangements_count=Count("arrangements", distinct=True)
                )
                .prefetch_related(
                    Prefetch(
                        "userships",
                        queryset=EnsembleUsership.objects.filter(user=user).only(
                            "id", "user_id", "ensemble_id", "role"
                        ),
                    )
                )
                .order_by("id")
                .distinct()
            )

        arrangements_queryset = Arrangement.objects.select_related(
            "ensemble"
        ).prefetch_related(
            Prefetch(
                "versions",
                queryset=ArrangementVersion.objects.filter(is_latest=True),
                to_attr="prefetched_latest_versions",
            )
        )

        return base_qs.prefetch_related(
            Prefetch("arrangements", queryset=arrangements_queryset),
            Prefetch(
                "userships",
                queryset=EnsembleUsership.objects.select_related("user"),
            ),
            "part_names",
            Prefetch(
                "part_books",
                queryset=PartBook.objects.select_related("part_name").order_by(
                    "part_name__display_name", "-revision"
                ),
            ),
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        EnsembleUsership.objects.create(
            ensemble=serializer.instance,
            user=self.request.user,
            role=EnsembleUsership.Role.ADMIN,
        )

    @action(detail=True, methods=["get"], url_path="arrangements")
    def arrangements(self, request, slug=None):
        ensemble = self.get_object()
        if not self._has_access(ensemble, request.user):
            return Response(
                {"detail": "You do not have access to this ensemble."},
                status=status.HTTP_403_FORBIDDEN,
            )

        arrangements = (
            ensemble.arrangements.annotate(
                _has_unversioned_latest_commit=Exists(
                    Commit.objects.filter(
                        arrangement=OuterRef("pk"),
                        children__isnull=True,
                        version__isnull=True,
                    )
                ),
                _has_unresolved_comments_on_latest_version=Exists(
                    ArrangementVersionCommentThread.objects.filter(
                        arrangement_version__arrangement=OuterRef("pk"),
                        arrangement_version__is_latest=True,
                        status=ArrangementVersionCommentThread.Status.OPEN,
                    )
                ),
                first_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^([0-9]+)'))[1] AS INTEGER)",
                    [],
                ),
                second_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^[0-9]+(?:-|m)([0-9]+)'))[1] AS INTEGER)",
                    [],
                ),
            ).order_by("first_num", "second_num", "mvt_no")
        )
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)

    def _has_access(self, ensemble, user):
        return (
            ensemble.owner == user
            or EnsembleUsership.objects.filter(ensemble=ensemble, user=user).exists()
        )

    @action(detail=True, methods=["get", "post"], url_path="invite-link")
    def invite_link(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        is_owner = ensemble.owner == user
        is_admin = user.get_ensemble_role(ensemble) == EnsembleUsership.Role.ADMIN

        if not is_owner and not is_admin:
            return Response(
                {
                    "detail": "Only ensemble owners and admins can generate invite links."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        token = ensemble.get_or_create_invite_token()
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        join_url = f"{frontend_url.rstrip('/')}/join/{token}"

        return Response(
            {
                "invite_token": token,
                "join_url": join_url,
                "ensemble_name": ensemble.name,
                "ensemble_slug": ensemble.slug,
            }
        )

    @action(detail=True, methods=["post"], url_path="remove-user")
    def remove_user(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        if user.is_ensemble_admin(ensemble) is False:
            return Response(
                {"detail": "Only admins can remove users."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"detail": "User ID is required to remove a user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usership = EnsembleUsership.objects.get(ensemble=ensemble, user__id=user_id)
            usership.delete()
            return Response(
                {"detail": "User removed from ensemble."}, status=status.HTTP_200_OK
            )
        except EnsembleUsership.DoesNotExist:
            return Response(
                {"detail": "User is not a member of this ensemble."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"], url_path="change-user-role")
    def change_user_role(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        if user.get_ensemble_role(ensemble) != EnsembleUsership.Role.ADMIN:
            return Response(
                {"detail": "Only admins can change user roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.data.get("user_id")
        new_role = request.data.get("role")

        if not user_id:
            return Response(
                {"detail": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not new_role:
            return Response(
                {"detail": "Role is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        valid_roles = [choice[0] for choice in EnsembleUsership.Role.choices]
        if new_role not in valid_roles:
            return Response(
                {"detail": f"Invalid role. Must be one of: {', '.join(valid_roles)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            usership = EnsembleUsership.objects.get(ensemble=ensemble, user__id=user_id)
            usership.role = new_role
            usership.save(update_fields=["role"])
            return Response(
                {"detail": "User role updated successfully.", "role": usership.role},
                status=status.HTTP_200_OK,
            )
        except EnsembleUsership.DoesNotExist:
            return Response(
                {"detail": "User is not a member of this ensemble."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"], url_path="part-name-matrix")
    def part_name_matrix(self, request, slug=None):
        ensemble = self.get_object()
        if not self._has_access(ensemble, request.user):
            return Response(
                {"detail": "You do not have access to this ensemble."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(build_part_name_matrix(ensemble))

    @action(detail=True, methods=["post"], url_path="rename-part-name")
    def rename_part_name(self, request, slug=None):
        ensemble = self.get_object()
        if not request.user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can rename part names."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EnsemblePartNameRenameSerializer(
            data=request.data, context={"ensemble": ensemble}
        )
        serializer.is_valid(raise_exception=True)
        part = serializer.validated_data["part"]
        display_name = serializer.validated_data["display_name"]

        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            part.rename_display_name(display_name)
        except DjangoValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"id": part.id, "display_name": part.display_name},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def merge_part_names(self, request, slug=None):
        ensemble = self.get_object()
        if not request.user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can merge part names."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EnsemblePartNameMergeSerializer(
            data=request.data, context={"ensemble": ensemble}
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        first = validated_data["first_part"]
        second = validated_data["second_part"]

        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            merged = PartName.merge_part_names(
                first, second, validated_data.get("new_displayname", "") or ""
            )
        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"id": merged.id, "display_name": merged.display_name},
            status=status.HTTP_200_OK,
        )

    def _parse_layout_overrides(self, raw_overrides) -> dict[int, str] | Response:
        if raw_overrides is None:
            return {}
        if not isinstance(raw_overrides, dict):
            return Response(
                {"detail": "layout_overrides must be an object mapping part name IDs to layouts."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parsed: dict[int, str] = {}
        for key, value in raw_overrides.items():
            try:
                part_id = int(key)
            except (TypeError, ValueError):
                return Response(
                    {"detail": f"Invalid part name ID in layout_overrides: {key}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if value is not None and value not in VALID_LAYOUTS:
                return Response(
                    {"detail": f"Invalid layout '{value}'. Must be one of: {sorted(VALID_LAYOUTS)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if value is not None:
                parsed[part_id] = value
        return parsed

    @action(detail=True, methods=["post"])
    def generate_part_books(self, request, slug=None):
        ensemble = self.get_object()
        layout_overrides = self._parse_layout_overrides(
            request.data.get("layout_overrides")
        )
        if isinstance(layout_overrides, Response):
            return layout_overrides
        generate_books_for_ensemble.delay(ensemble.id, layout_overrides=layout_overrides)
        return Response(
            {"detail": "Export of Part Books triggered"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="generate-part-book")
    def generate_single_part_book(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        if not user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can generate part books."},
                status=status.HTTP_403_FORBIDDEN,
            )

        part_name_id = request.data.get("part_name_id")
        if not part_name_id:
            return Response(
                {"detail": "part_name_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            part_name = PartName.objects.get(id=part_name_id, ensemble=ensemble)
        except PartName.DoesNotExist:
            return Response(
                {"detail": "Part name not found for this ensemble."},
                status=status.HTTP_404_NOT_FOUND,
            )

        one_off_layout = request.data.get("layout")
        if one_off_layout is not None and one_off_layout not in VALID_LAYOUTS:
            return Response(
                {"detail": f"Invalid layout '{one_off_layout}'. Must be one of: {sorted(VALID_LAYOUTS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ensemble.part_books_generating:
            return Response(
                {"detail": "Part books are already generating."},
                status=status.HTTP_409_CONFLICT,
            )

        ensemble.part_books_generating = True
        revision = ensemble.latest_part_book_revision + 1
        ensemble.save(update_fields=["part_books_generating"])

        generate_part_book.delay(
            ensemble.id,
            part_name.id,
            revision,
            one_off_layout=one_off_layout,
            solo=True,
        )
        ensemble.latest_part_book_revision = revision
        ensemble.save(update_fields=["latest_part_book_revision"])

        return Response(
            {
                "detail": f"Export of part book for {part_name.display_name} triggered",
                "revision": revision,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="update-part-book-layout")
    def update_part_book_layout(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        if not user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can update part book layout."},
                status=status.HTTP_403_FORBIDDEN,
            )

        part_layouts = request.data.get("part_layouts", [])
        if not isinstance(part_layouts, list):
            return Response(
                {
                    "detail": "part_layouts must be a list of objects with 'id' and 'part_book_layout_override' fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_layouts = {choice[0] for choice in PART_BOOK_LAYOUT_CHOICES}
        part_ids = [item.get("id") for item in part_layouts if item.get("id")]
        if not part_ids:
            return Response(
                {"detail": "No part IDs provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        parts = PartName.objects.filter(id__in=part_ids, ensemble=ensemble)
        if parts.count() != len(part_ids):
            return Response(
                {
                    "detail": "One or more part IDs are invalid or do not belong to this ensemble."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        layout_by_id = {}
        for item in part_layouts:
            part_id = item.get("id")
            if part_id is None:
                continue
            override = item.get("part_book_layout_override")
            if override is not None and override not in valid_layouts:
                return Response(
                    {"detail": f"Invalid layout '{override}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            layout_by_id[part_id] = override

        for part in parts:
            if part.id in layout_by_id:
                part.part_book_layout_override = layout_by_id[part.id]
                part.save(update_fields=["part_book_layout_override"])

        return Response(
            {"detail": "Part book layout updated successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="update-part-order")
    def update_part_order(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        if not user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can update part order."},
                status=status.HTTP_403_FORBIDDEN,
            )

        part_orders = request.data.get("part_orders", [])

        if not isinstance(part_orders, list):
            return Response(
                {
                    "detail": "part_orders must be a list of objects with 'id' and 'order' fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_ids = [item.get("id") for item in part_orders if item.get("id")]
        if not part_ids:
            return Response(
                {"detail": "No part IDs provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        parts = PartName.objects.filter(id__in=part_ids, ensemble=ensemble)
        if parts.count() != len(part_ids):
            return Response(
                {
                    "detail": "One or more part IDs are invalid or do not belong to this ensemble."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_dict = {
            item.get("id"): item.get("order")
            for item in part_orders
            if item.get("id") is not None
        }
        for part in parts:
            if part.id in part_dict:
                part.order = part_dict[part.id]
                part.save(update_fields=["order"])

        return Response(
            {"detail": "Part order updated successfully."}, status=status.HTTP_200_OK
        )
