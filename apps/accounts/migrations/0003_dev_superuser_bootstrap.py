"""Dev-superuser bootstrap: ensures `bob` exists on every migrate under DEBUG.

The config's development-data contract names this migration as the only
bootstrap: on a fresh dev database `migrate` materializes the dev superuser
`bob`; production migrations (DEBUG off) never create it.
"""

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations

DEV_SUPERUSER_USERNAME = "bob"
DEV_SUPERUSER_EMAIL = "bob@example.com"
DEV_SUPERUSER_PASSWORD = "bob-ig-pass-1"


def create_dev_superuser(apps, schema_editor):
    if not settings.DEBUG:
        return
    User = apps.get_model("accounts", "User")
    if User._default_manager.filter(username=DEV_SUPERUSER_USERNAME).exists():
        return
    user = User(
        username=DEV_SUPERUSER_USERNAME,
        email=DEV_SUPERUSER_EMAIL,
        is_staff=True,
        is_superuser=True,
    )
    # Trusted direct hash assignment: the pre-computed hash is marked as
    # such so the storage path stores it as-is instead of hashing it again
    # (historical model instances accept arbitrary attributes).
    user.password = make_password(DEV_SUPERUSER_PASSWORD)
    user._password_is_hash = True
    user.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_dev_superuser, migrations.RunPython.noop),
    ]
