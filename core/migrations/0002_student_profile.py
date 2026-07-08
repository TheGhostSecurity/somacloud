from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_seed_default_admin"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profile_image", models.ImageField(blank=True, null=True, upload_to="student-profiles/")),
                (
                    "user",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="student_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
