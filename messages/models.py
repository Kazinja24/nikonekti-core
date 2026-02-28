from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    application = models.OneToOneField(
        "applications.RentalApplication",
        on_delete=models.SET_NULL,
        related_name="conversation",
        null=True,
        blank=True,
    )
    # Optional property-level conversation (contact landlord without an application)
    property_obj = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    # The user who initiated a property-contact conversation
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["updated_at"]),
            models.Index(fields=["initiator"]),
        ]

    def clean(self):
        if not self.application_id and not self.property_obj_id:
            raise ValidationError("A conversation must be linked to either an application or a property")

    def __str__(self):
        if self.application_id:
            return f"Conversation for application {self.application_id}"
        if self.property_obj_id:
            return f"Conversation for property {self.property_obj_id}"
        return f"Conversation {self.id}"

    @property
    def tenant(self):
        if self.application_id:
            return self.application.tenant
        # For property conversations, initiator is the user who contacted landlord
        return self.initiator

    @property
    def landlord(self):
        if self.application_id:
            return self.application.property.owner
        if self.property_obj_id:
            return self.property_obj.owner
        return None

    @property
    def property(self):
        if self.application_id:
            return self.application.property
        return self.property_obj

    def has_participant(self, user):
        return user == self.tenant or user == self.landlord


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_messages",
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"Message {self.id} in conversation {self.conversation_id}"
