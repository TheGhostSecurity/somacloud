from django.contrib.auth.hashers import check_password, make_password
from django.db import migrations


def disable_unsafe_seeded_admin_password(apps, schema_editor):
    User = apps.get_model("auth", "User")

    try:
        user = User.objects.get(username="ghostriley")
    except User.DoesNotExist:
        return

    if check_password("1234", user.password):
        user.password = make_password(None)
        user.save(update_fields=["password"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_student_profile"),
    ]

    operations = [
        migrations.RunPython(disable_unsafe_seeded_admin_password, noop),
    ]
