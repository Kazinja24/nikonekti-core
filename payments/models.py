import uuid
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import timedelta


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=100, unique=True)

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        related_name="payments",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["tenant"]),
            models.Index(fields=["property"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.COMPLETED, self.Status.FAILED},
            self.Status.COMPLETED: set(),
            self.Status.FAILED: {self.Status.PENDING},
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")
        with transaction.atomic():
            self.status = target_status
            self.full_clean()
            self.save()

    def __str__(self):
        return f"{self.reference} - {self.amount}"


class RentInvoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.PROTECT,
        related_name="rent_invoices",
    )
    month = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["lease", "month"], name="uniq_invoice_per_lease_month"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["lease"]),
            models.Index(fields=["month"]),
            models.Index(fields=["status", "due_date"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.PAID, self.Status.OVERDUE},
            self.Status.OVERDUE: {self.Status.PAID},
            self.Status.PAID: set(),
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")

        with transaction.atomic():
            self.status = target_status
            if target_status == self.Status.PAID and not self.paid_at:
                self.paid_at = timezone.now()
            self.full_clean()
            self.save()

    def __str__(self):
        return f"{self.lease_id} {self.month} ({self.status})"


class ListingPlan(models.Model):
    class Code(models.TextChoices):
        BASIC = "BASIC", "Basic"
        FEATURED = "FEATURED", "Featured"

    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    duration_days = models.PositiveIntegerField(default=30)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} ({self.price})"


class ListingPaymentIntent(models.Model):
    class Status(models.TextChoices):
        INTENT_CREATED = "intent_created", "Intent Created"
        PENDING_CONFIRMATION = "pending_confirmation", "Pending Confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"
        OVERRIDDEN = "overridden", "Overridden"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        related_name="listing_intents",
    )
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="listing_payment_intents",
    )
    plan = models.ForeignKey(ListingPlan, on_delete=models.PROTECT, related_name="payment_intents")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.INTENT_CREATED)
    payment_reference = models.CharField(max_length=150, blank=True)
    payment_proof = models.FileField(upload_to="listing_payments/proofs/", null=True, blank=True)
    landlord_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_listing_payment_intents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["landlord"]),
            models.Index(fields=["property"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.property_id} - {self.plan.code} ({self.status})"

    def can_activate(self):
        return self.status in {self.Status.INTENT_CREATED, self.Status.PENDING_CONFIRMATION}

    def activate(self, reviewed_by, override=False, admin_note=""):
        if not self.can_activate():
            raise ValueError(f"Cannot activate intent with status '{self.status}'")
        now = timezone.now()
        with transaction.atomic():
            self.status = self.Status.OVERRIDDEN if override else self.Status.CONFIRMED
            self.confirmed_by = reviewed_by
            self.reviewed_at = now
            self.admin_note = admin_note
            self.starts_at = now
            self.expires_at = now + timedelta(days=self.plan.duration_days)
            self.save(
                update_fields=[
                    "status",
                    "confirmed_by",
                    "reviewed_at",
                    "admin_note",
                    "starts_at",
                    "expires_at",
                ]
            )

    @classmethod
    def has_active_paid_listing(cls, property_id):
        now = timezone.now()
        return cls.objects.filter(
            property_id=property_id,
            status__in=[cls.Status.CONFIRMED, cls.Status.OVERRIDDEN],
            expires_at__gt=now,
        ).exists()
