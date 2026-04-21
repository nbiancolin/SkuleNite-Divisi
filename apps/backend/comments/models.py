from django.conf import settings
from django.db import models

from ensembles.models import ArrangementVersion


class ArrangementVersionCommentThread(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "open"
        RESOLVED = "resolved", "resolved"

    arrangement_version = models.ForeignKey(
        ArrangementVersion,
        related_name="comment_threads",
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="created_arrangement_version_comment_threads",
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    page_number = models.PositiveIntegerField()
    x = models.FloatField()
    y = models.FloatField()
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="resolved_arrangement_version_comment_threads",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ArrangementVersionComment(models.Model):
    thread = models.ForeignKey(
        ArrangementVersionCommentThread,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="arrangement_version_comments",
        on_delete=models.CASCADE,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
