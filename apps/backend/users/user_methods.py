from django.contrib.auth import get_user_model
from ensembles.models import EnsembleUsership

User = get_user_model()

def is_ensemble_admin(self, ensemble) -> bool:
    # Check if user is owner or has admin role in usership
    if ensemble.owner == self:
        return True
    return EnsembleUsership.objects.filter(
        user=self,
        ensemble=ensemble,
        role=EnsembleUsership.Role.ADMIN,
    ).exists()

User.add_to_class("is_ensemble_admin", is_ensemble_admin)

def get_ensemble_role(self, ensemble):
    try:
        return EnsembleUsership.objects.get(user=self, ensemble=ensemble).role
    except EnsembleUsership.DoesNotExist:
        return None

User.add_to_class("get_ensemble_role", get_ensemble_role)