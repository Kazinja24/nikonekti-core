import uuid
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_is_verified_landlord"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="user",
            name="id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["role"], name="users_user_role_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["is_verified_landlord"], name="users_user_verified_idx"),
        ),
    ]
