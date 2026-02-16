from django.db import models
import uuid
from django.conf import settings
from properties.models import Property
from viewings.models import Viewing


class Lease(models.Model):
    STATUS_CHOICES = [
        ("LEASED", "Leased"),
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_leases",
    )
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="landlord_leases",
    )
    viewing = models.ForeignKey(
        Viewing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    application = models.OneToOneField(
        "applications.RentalApplication",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lease",
    )

    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="LEASED")
    contract_file = models.FileField(upload_to="contracts/", null=True, blank=True)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.property.title} - {self.tenant}"
