import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class Lease(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="leases",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tenant_leases",
    )
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="landlord_leases",
    )
    viewing = models.ForeignKey(
        "viewings.Viewing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leases",
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
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    contract_file = models.FileField(upload_to="contracts/", null=True, blank=True)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)
    tenant_confirmed_at = models.DateTimeField(null=True, blank=True)
    landlord_confirmed_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tenant"]),
            models.Index(fields=["landlord"]),
            models.Index(fields=["property"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["status", "end_date"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.ACTIVE},
            self.Status.ACTIVE: {self.Status.EXPIRED, self.Status.TERMINATED},
            self.Status.EXPIRED: set(),
            self.Status.TERMINATED: set(),
        }
        return target_status in transitions.get(self.status, set())

    def is_fully_confirmed(self):
        return bool(self.tenant_confirmed_at and self.landlord_confirmed_at)

    def mark_tenant_confirmed(self):
        with transaction.atomic():
            self.tenant_confirmed_at = self.tenant_confirmed_at or timezone.now()
            if self.is_fully_confirmed():
                self.is_signed = True
                if not self.signed_at:
                    self.signed_at = timezone.now()
            self.full_clean()
            self.save(update_fields=["tenant_confirmed_at", "is_signed", "signed_at"])

    def mark_landlord_confirmed(self):
        with transaction.atomic():
            self.landlord_confirmed_at = self.landlord_confirmed_at or timezone.now()
            if self.is_fully_confirmed():
                self.is_signed = True
                if not self.signed_at:
                    self.signed_at = timezone.now()
            self.full_clean()
            self.save(update_fields=["landlord_confirmed_at", "is_signed", "signed_at"])

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")

        with transaction.atomic():
            self.status = target_status

            if target_status == self.Status.ACTIVE:
                if not self.is_fully_confirmed():
                    raise ValueError("Both tenant and landlord must confirm before activation.")
                self.is_signed = True
                if not self.signed_at:
                    self.signed_at = timezone.now()
            elif target_status == self.Status.TERMINATED:
                self.terminated_at = timezone.now()

            self.full_clean()
            self.save()

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")

    def __str__(self):
        return f"{self.property} - {self.tenant} ({self.status})"
