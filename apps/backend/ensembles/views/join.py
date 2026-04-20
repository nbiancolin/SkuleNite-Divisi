from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ensembles.models import Ensemble, EnsembleUsership


class JoinEnsembleView(APIView):
    """View to join an ensemble using an invite token"""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required to join an ensemble."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token = request.data.get("token") or kwargs.get("token")

        if not token:
            return Response(
                {"detail": "Invite token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ensemble = Ensemble.objects.get(invite_token=token)
        except Ensemble.DoesNotExist:
            return Response(
                {"detail": "Invalid invite token."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user

        if ensemble.owner == user:
            return Response(
                {
                    "detail": "You are already the owner of this ensemble.",
                    "ensemble": {
                        "id": ensemble.id,
                        "name": ensemble.name,
                        "slug": ensemble.slug,
                    },
                },
                status=status.HTTP_200_OK,
            )

        if EnsembleUsership.objects.filter(ensemble=ensemble, user=user).exists():
            return Response(
                {
                    "detail": "You are already a member of this ensemble.",
                    "ensemble": {
                        "id": ensemble.id,
                        "name": ensemble.name,
                        "slug": ensemble.slug,
                    },
                },
                status=status.HTTP_200_OK,
            )

        EnsembleUsership.objects.create(ensemble=ensemble, user=user)

        return Response(
            {
                "detail": "Successfully joined the ensemble.",
                "ensemble": {
                    "id": ensemble.id,
                    "name": ensemble.name,
                    "slug": ensemble.slug,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token") or kwargs.get("token")

        if not token:
            return Response(
                {"detail": "Invite token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ensemble = Ensemble.objects.get(invite_token=token)
        except Ensemble.DoesNotExist:
            return Response(
                {"detail": "Invalid invite token."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "ensemble": {
                    "id": ensemble.id,
                    "name": ensemble.name,
                    "slug": ensemble.slug,
                },
                "is_authenticated": request.user.is_authenticated,
                "already_member": (
                    request.user.is_authenticated
                    and (
                        ensemble.owner == request.user
                        or EnsembleUsership.objects.filter(ensemble=ensemble, user=request.user).exists()
                    )
                )
                if request.user.is_authenticated
                else False,
            }
        )
