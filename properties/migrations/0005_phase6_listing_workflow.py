# Generated migration for Phase 6: listing workflow and review system

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0004_property_verification_and_publish_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create Feature model
        migrations.CreateModel(
            name="Feature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        # Add M2M field for features on Property
        migrations.AddField(
            model_name="property",
            name="features",
            field=models.ManyToManyField(blank=True, related_name="properties", to="properties.feature"),
        ),
        # Add listing workflow fields to Property
        migrations.AddField(
            model_name="property",
            name="listing_status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending_review", "Pending Review"),
                    ("published", "Published"),
                    ("rejected", "Rejected"),
                    ("unlisted", "Unlisted"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submitted_properties",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_properties",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="property",
            name="admin_review_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="property",
            name="priority_score",
            field=models.IntegerField(default=0),
        ),
        # Add thumbnail field to PropertyImage
        migrations.AddField(
            model_name="propertyimage",
            name="thumbnail",
            field=models.ImageField(blank=True, null=True, upload_to="properties/thumbnails/"),
        ),
        # Create PropertyReviewLog model
        migrations.CreateModel(
            name="PropertyReviewLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("verified", "Verified"),
                            ("rejected_verification", "Rejected Verification"),
                        ],
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "admin",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="property_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "property",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_logs",
                        to="properties.property",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
