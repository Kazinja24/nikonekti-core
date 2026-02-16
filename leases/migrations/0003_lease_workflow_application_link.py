import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0003_application_workflow_constraints"),
        ("leases", "0002_lease_contract_file_is_signed"),
    ]

    operations = [
        migrations.AddField(
            model_name="lease",
            name="application",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lease",
                to="applications.rentalapplication",
            ),
        ),
        migrations.AlterField(
            model_name="lease",
            name="status",
            field=models.CharField(
                choices=[("LEASED", "Leased"), ("ACTIVE", "Active"), ("CLOSED", "Closed")],
                default="LEASED",
                max_length=20,
            ),
        ),
    ]
