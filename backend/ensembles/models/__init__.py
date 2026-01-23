from ensembles.models.ensemble import Ensemble
from ensembles.models.ensemble_usership import EnsembleUsership
from ensembles.models.arrangement import Arrangement
from ensembles.models.arrangement_version import ArrangementVersion
from ensembles.models.part import PartAsset, PartBook, PartBookEntry, PartName
from ensembles.models.export_failure_log import ExportFailureLog

from ensembles.models.diff import Diff


#holdover from an old migration, can't delete this without squashing migrations (or editing old migrations, both of which I dont want to deal with in prod)

def _part_upload_key(instance, filename):
    """Generate storage key for part files"""
    ensemble_slug = instance.version.arrangement.ensemble.slug
    arrangement_slug = instance.version.arrangement.slug
    version = instance.version.version_label
    return f"ensembles/{ensemble_slug}/arrangements/{arrangement_slug}/versions/{version}/parts/{filename}"

_part_upload_path = _part_upload_key