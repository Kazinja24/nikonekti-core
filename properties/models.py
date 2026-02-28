import logging

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


User = settings.AUTH_USER_MODEL
logger = logging.getLogger(__name__)


class Property(models.Model):
    PROPERTY_STATUS = (
        ("available", "Available"),
        ("rented", "Rented"),
        ("unavailable", "Unavailable"),
    )
    VERIFICATION_STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="properties")
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    features = models.ManyToManyField(
        "Feature",
        blank=True,
        related_name="properties",
    )
    status = models.CharField(max_length=20, choices=PROPERTY_STATUS, default="available")
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default="pending")
    ownership_document = models.FileField(upload_to="verification/properties/ownership/", null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_properties",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    LISTING_STATUS = (
        ("draft", "Draft"),
        ("pending_review", "Pending Review"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    )

    listing_status = models.CharField(max_length=30, choices=LISTING_STATUS, default="draft")
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_properties",
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_properties",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_review_notes = models.TextField(blank=True)
    priority_score = models.FloatField(default=0.0)

    def can_be_published(self):
        return (
            self.owner.is_verified_landlord
            and self.verification_status == "approved"
            and bool(self.description and self.description.strip())
            and self.price is not None
            and self.price > 0
            and self.images.exists()
        )

    def can_be_monetized(self):
        return self.can_be_published()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["listing_status"]),
            models.Index(fields=["location"]),
            models.Index(fields=["price"]),
            models.Index(fields=["priority_score"]),
            models.Index(fields=["status", "listing_status", "verification_status"]),
        ]

    def __str__(self):
        return self.title


class Feature(models.Model):
    """Master list of property features/amenities that landlords can select from."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PropertyReviewLog(models.Model):
    ACTION_CHOICES = (
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("submitted", "Submitted"),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="review_logs")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="property_review_logs")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.property.title} - {self.action} by {self.admin}"


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="property_images/")
    thumbnail = models.ImageField(upload_to="property_images/thumbnails/", null=True, blank=True)
    is_cover = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"

    def save(self, *args, **kwargs):
        # Save original first
        super().save(*args, **kwargs)

        # Generate a thumbnail (small) if not present
        try:
            from PIL import Image
            from io import BytesIO
            from django.core.files.base import ContentFile
            from django.conf import settings

            if not self.image:
                return

            img = Image.open(self.image.path)
            img_format = img.format if hasattr(img, 'format') else None
            # Normalize format
            if img_format and img_format.upper() not in getattr(settings, 'IMAGE_ALLOWED_FORMATS', ['JPEG', 'JPG', 'PNG']):
                return

            thumb_size = (800, 600)
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            img.thumbnail(thumb_size, resample)

            temp_io = BytesIO()
            save_format = 'JPEG' if img.mode in ('RGB', 'L', 'RGBA') else 'PNG'
            if img.mode == 'RGBA':
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                bg.save(temp_io, format=save_format, quality=85)
            else:
                img.save(temp_io, format=save_format, quality=85)

            thumb_name = f"thumb_{self.pk}_{self.image.name.split('/')[-1]}"
            self.thumbnail.save(thumb_name, ContentFile(temp_io.getvalue()), save=False)
            super().save(update_fields=['thumbnail'])
        except Exception as exc:
            logger.error(
                "Thumbnail generation failed for property image id=%s: %s",
                self.pk,
                exc,
                exc_info=True,
            )
            return
