from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Viewing(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="viewings",
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="viewing_requests",
    )
    application = models.ForeignKey(
        "applications.RentalApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewings",
    )

    scheduled_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "property"],
                condition=models.Q(status__in=["pending", "approved"]),
                name="uniq_active_viewing_per_tenant_property",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tenant"]),
            models.Index(fields=["property"]),
            models.Index(fields=["scheduled_date"]),
            models.Index(fields=["status", "scheduled_date"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.APPROVED, self.Status.REJECTED},
            self.Status.APPROVED: {self.Status.COMPLETED, self.Status.REJECTED},
            self.Status.REJECTED: set(),
            self.Status.COMPLETED: set(),
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")
        with transaction.atomic():
            self.status = target_status
            self.full_clean()
            self.save()

    def clean(self):
        if self.scheduled_date and self.scheduled_date < timezone.now():
            raise ValidationError("Viewing cannot be scheduled in the past")

    def __str__(self):
        return f"{self.tenant} -> {self.property} ({self.status})"
