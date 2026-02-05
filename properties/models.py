from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Property(models.Model):

    PROPERTY_STATUS = (
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('unavailable', 'Unavailable'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')

    title = models.CharField(max_length=200)
    description = models.TextField()

    location = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=PROPERTY_STATUS, default='available')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
