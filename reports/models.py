from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class PropertyReport(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    class Reason(models.TextChoices):
        FAKE_LISTING = "fake_listing", "Fake or fraudulent listing"
        WRONG_PRICE = "wrong_price", "Incorrect pricing information"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        ALREADY_RENTED = "already_rented", "Property already rented"
        SCAM = "scam", "Suspected scam"
        OTHER = "other", "Other"

    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="property_reports_made",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports",
    )
    reason = models.CharField(max_length=50, choices=Reason.choices)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_reports_reviewed",
    )
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "property"],
                condition=models.Q(
                    status__in=[
                        "pending",
                        "under_review",
                    ]
                ),
                name="uniq_open_property_report_per_user_property",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reporter"]),
            models.Index(fields=["property"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["reviewed_by"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.UNDER_REVIEW, self.Status.DISMISSED},
            self.Status.UNDER_REVIEW: {self.Status.RESOLVED, self.Status.DISMISSED},
            self.Status.RESOLVED: set(),
            self.Status.DISMISSED: set(),
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status, reviewed_by=None):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")
        with transaction.atomic():
            self.status = target_status
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.full_clean()
            self.save()

    def __str__(self):
        return f"Report {self.id} on property {self.property_id} ({self.status})"


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="blocks_made",
    )
    blocked_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="blocks_received",
    )
    reason = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked_user"],
                condition=models.Q(is_active=True),
                name="uniq_active_block_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["blocker"]),
            models.Index(fields=["blocked_user"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["blocker", "blocked_user", "is_active"]),
        ]

    def clean(self):
        if self.blocker_id == self.blocked_user_id:
            raise ValidationError("A user cannot block themselves")

    def __str__(self):
        return f"{self.blocker_id} blocked {self.blocked_user_id}"
