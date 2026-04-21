from django.db.models import Q

from ensembles.models import ArrangementVersion


def get_accessible_versions_for_user(user):
    if not user.is_authenticated:
        return ArrangementVersion.objects.none()

    return ArrangementVersion.objects.filter(
        Q(arrangement__ensemble__owner=user) | Q(arrangement__ensemble__userships__user=user)
    ).distinct()

