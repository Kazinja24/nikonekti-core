import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator


class RentalOffer(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="rental_offers",
    )
    application = models.OneToOneField(
        "applications.RentalApplication",
        on_delete=models.PROTECT,
        related_name="offer",
    )
    viewing = models.ForeignKey(
        "viewings.Viewing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_rental_offers",
    )
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_rental_offers",
    )
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    start_date = models.DateField()
    end_date = models.DateField()
    landlord_note = models.TextField(blank=True)
    tenant_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tenant"]),
            models.Index(fields=["landlord"]),
            models.Index(fields=["property"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.SENT: {
                self.Status.ACCEPTED,
                self.Status.REJECTED,
                self.Status.WITHDRAWN,
                self.Status.EXPIRED,
            },
            self.Status.ACCEPTED: set(),
            self.Status.REJECTED: set(),
            self.Status.WITHDRAWN: set(),
            self.Status.EXPIRED: set(),
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")

        with transaction.atomic():
            self.status = target_status
            self.responded_at = timezone.now()
            self.full_clean()
            self.save()

    def clean(self):
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError("Offer end date must be after start date.")

    def __str__(self):
        return f"{self.property} offer to {self.tenant} ({self.status})"

