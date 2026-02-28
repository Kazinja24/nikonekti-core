# Migration for property-level conversations support

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chat_messages", "0001_initial"),
        ("properties", "0005_phase6_listing_workflow"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Make application optional
        migrations.AlterField(
            model_name="conversation",
            name="application",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversation",
                to="applications.rentalapplication",
            ),
        ),
        # Add property_obj FK
        migrations.AddField(
            model_name="conversation",
            name="property_obj",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="properties.property",
            ),
        ),
        # Add initiator FK
        migrations.AddField(
            model_name="conversation",
            name="initiator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="initiated_conversations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
