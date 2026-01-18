from django.db import models

from ensembles.models.arrangement_version import ArrangementVersion

from logging import getLogger

logger = getLogger("app")

class ExportFailureLog(models.Model):
    arrangement_version = models.ForeignKey(ArrangementVersion, related_name="failure_log", on_delete=models.CASCADE)
    #Auto-populated with info from 
    error_msg = models.CharField()

    #info that I may want to add
    comments = models.CharField()

    @property
    def arrangement_version__str__(self):
        return self.arrangement_version.__str__()