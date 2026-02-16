import uuid
from django.db import models
from users.models import User
from properties.models import Property
from viewings.models import Viewing


class RentalApplication(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("VIEWING_SCHEDULED", "Viewing Scheduled"),
        ("ACCEPTED", "Accepted"),
        ("LEASED", "Leased"),
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("REJECTED", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="applications")
    viewing = models.ForeignKey(Viewing, on_delete=models.SET_NULL, null=True, blank=True)

    message = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    landlord_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "property"],
                condition=models.Q(
                    status__in=[
                        "PENDING",
                        "APPROVED",
                        "VIEWING_SCHEDULED",
                        "ACCEPTED",
                        "LEASED",
                        "ACTIVE",
                    ]
                ),
                name="uniq_active_application_per_tenant_property",
            )
        ]

    def __str__(self):
        return f"{self.tenant.email} -> {self.property.title} ({self.status})"
