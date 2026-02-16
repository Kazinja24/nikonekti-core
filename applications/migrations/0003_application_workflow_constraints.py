from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0002_alter_rentalapplication_viewing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rentalapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("APPROVED", "Approved"),
                    ("VIEWING_SCHEDULED", "Viewing Scheduled"),
                    ("ACCEPTED", "Accepted"),
                    ("LEASED", "Leased"),
                    ("ACTIVE", "Active"),
                    ("CLOSED", "Closed"),
                    ("REJECTED", "Rejected"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="rentalapplication",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="rentalapplication",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["PENDING", "APPROVED", "VIEWING_SCHEDULED", "ACCEPTED", "LEASED", "ACTIVE"]),
                fields=("tenant", "property"),
                name="uniq_active_application_per_tenant_property",
            ),
        ),
    ]
