from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.db.models.expressions import RawSQL
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ensembles.models import (
    Arrangement,
    ArrangementVersion,
    Ensemble,
    EnsembleUsership,
    PartBook,
    PartName,
)
from ensembles.serializers import (
    ArrangementSerializer,
    EnsembleListSerializer,
    EnsemblePartNameMergeSerializer,
    EnsembleSerializer,
)
from ensembles.tasks.part_books import generate_books_for_ensemble


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

        base_qs = Ensemble.objects.filter(Q(owner=user) | Q(userships__user=user)).select_related("owner")

        if self.action == "list":
            return base_qs.annotate(arrangements_count=Count("arrangements", distinct=True)).prefetch_related(
                Prefetch(
                    "userships",
                    queryset=EnsembleUsership.objects.filter(user=user).only(
                        "id", "user_id", "ensemble_id", "role"
                    ),
                )
            ).order_by("id").distinct()

        arrangements_queryset = Arrangement.objects.select_related("ensemble").prefetch_related(
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
        return ensemble.owner == user or EnsembleUsership.objects.filter(ensemble=ensemble, user=user).exists()

    @action(detail=True, methods=["get", "post"], url_path="invite-link")
    def invite_link(self, request, slug=None):
        ensemble = self.get_object()
        user = request.user

        is_owner = ensemble.owner == user
        is_admin = user.get_ensemble_role(ensemble) == EnsembleUsership.Role.ADMIN

        if not is_owner and not is_admin:
            return Response(
                {"detail": "Only ensemble owners and admins can generate invite links."},
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
            return Response({"detail": "User removed from ensemble."}, status=status.HTTP_200_OK)
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
            return Response({"detail": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not new_role:
            return Response({"detail": "Role is required."}, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=["post"])
    def merge_part_names(self, request, slug=None):
        serializer = EnsemblePartNameMergeSerializer(data=request.data, context={"ensemble": self.get_object()})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        first = validated_data["first_part"]
        second = validated_data["second_part"]

        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            merged = PartName.merge_part_names(first, second, validated_data.get("new_displayname", "") or "")
        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"id": merged.id, "display_name": merged.display_name},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def generate_part_books(self, request, slug=None):
        ensemble = self.get_object()
        generate_books_for_ensemble.delay(ensemble.id)
        return Response({"detail": "Export of Part Books triggered"}, status=status.HTTP_202_ACCEPTED)

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
                {"detail": "part_orders must be a list of objects with 'id' and 'order' fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_ids = [item.get("id") for item in part_orders if item.get("id")]
        if not part_ids:
            return Response({"detail": "No part IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        parts = PartName.objects.filter(id__in=part_ids, ensemble=ensemble)
        if parts.count() != len(part_ids):
            return Response(
                {"detail": "One or more part IDs are invalid or do not belong to this ensemble."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        part_dict = {item.get("id"): item.get("order") for item in part_orders if item.get("id") is not None}
        for part in parts:
            if part.id in part_dict:
                part.order = part_dict[part.id]
                part.save(update_fields=["order"])

        return Response({"detail": "Part order updated successfully."}, status=status.HTTP_200_OK)
