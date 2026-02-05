from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from properties.models import Property

User = settings.AUTH_USER_MODEL


class Viewing(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='viewings')
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewing_requests')

    scheduled_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant} -> {self.property}"
