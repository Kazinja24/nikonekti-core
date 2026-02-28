import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class RentalApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    ACTIVE_STATUSES = [Status.PENDING, Status.APPROVED]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="applications",
    )

    message = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    landlord_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "property"],
                condition=models.Q(status__in=["pending", "approved"]),
                name="uniq_active_application_per_tenant_property",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tenant"]),
            models.Index(fields=["property"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.APPROVED, self.Status.REJECTED, self.Status.EXPIRED},
            self.Status.APPROVED: {self.Status.REJECTED, self.Status.EXPIRED},
            self.Status.REJECTED: {self.Status.EXPIRED},
            self.Status.EXPIRED: set(),
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")
        self.status = target_status
        if target_status in [self.Status.APPROVED, self.Status.REJECTED]:
            self.decided_at = timezone.now()
        self.save()

    def __str__(self):
        tenant_display = self.tenant.email if self.tenant_id and hasattr(self.tenant, "email") else str(self.tenant)
        property_display = self.property.title if self.property_id and hasattr(self.property, "title") else str(self.property)
        return f"{tenant_display} -> {property_display} ({self.status})"
