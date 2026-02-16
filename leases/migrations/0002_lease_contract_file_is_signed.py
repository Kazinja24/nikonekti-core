from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lease",
            name="contract_file",
            field=models.FileField(blank=True, null=True, upload_to="contracts/"),
        ),
        migrations.AddField(
            model_name="lease",
            name="is_signed",
            field=models.BooleanField(default=False),
        ),
    ]
