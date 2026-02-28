from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


User = settings.AUTH_USER_MODEL


class LandlordVerification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    landlord = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="landlord_verification",
    )
    identity_document = models.FileField(upload_to="verification/landlords/identity/")
    landlord_supporting_document = models.FileField(upload_to="verification/landlords/supporting/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_landlord_verifications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["status", "submitted_at"]),
        ]

    def can_transition_to(self, target_status):
        transitions = {
            self.Status.PENDING: {self.Status.APPROVED, self.Status.REJECTED},
            self.Status.APPROVED: {self.Status.REJECTED},
            self.Status.REJECTED: {self.Status.PENDING},
        }
        return target_status in transitions.get(self.status, set())

    def transition_to(self, target_status, reviewed_by=None):
        if not self.can_transition_to(target_status):
            raise ValueError(f"Cannot transition from '{self.status}' to '{target_status}'")

        self.status = target_status
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()

        if target_status == self.Status.APPROVED:
            self.landlord.is_verified_landlord = True
            self.landlord.save(update_fields=["is_verified_landlord"])
        elif target_status == self.Status.REJECTED:
            self.landlord.is_verified_landlord = False
            self.landlord.save(update_fields=["is_verified_landlord"])

        self.full_clean()
        self.save()

    def clean(self):
        if self.reviewed_by and self.reviewed_by.role != "ADMIN":
            raise ValidationError("Only admins can review landlord verifications")

    def __str__(self):
        return f"{self.landlord} verification ({self.status})"
