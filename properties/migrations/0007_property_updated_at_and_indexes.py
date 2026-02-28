import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0006_remove_feature_created_at_alter_feature_slug_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["status"], name="prop_status_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["verification_status"], name="prop_verify_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["listing_status"], name="prop_listing_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["location"], name="prop_location_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["price"], name="prop_price_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["priority_score"], name="prop_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(
                fields=["status", "listing_status", "verification_status"],
                name="prop_pubflow_idx",
            ),
        ),
    ]
