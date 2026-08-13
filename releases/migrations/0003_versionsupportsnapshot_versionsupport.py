import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("releases", "0002_sourcesnapshot_parser_fields_releasesection_changeitem")]

    operations = [
        migrations.CreateModel(
            name="VersionSupportSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_url", models.URLField(max_length=500)),
                ("content_sha256", models.CharField(max_length=64, unique=True)),
                ("raw_html", models.TextField()),
                ("storage_path", models.CharField(max_length=500)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
                ("is_current", models.BooleanField(default=True)),
            ],
            options={"ordering": ["-fetched_at"]},
        ),
        migrations.CreateModel(
            name="VersionSupport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("series", models.CharField(max_length=16, unique=True)),
                ("current_minor", models.CharField(max_length=32)),
                ("supported", models.BooleanField()),
                ("first_release_date", models.DateField()),
                ("final_release_date", models.DateField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="support_rows", to="releases.versionsupportsnapshot")),
            ],
            options={"ordering": ["-first_release_date"]},
        ),
    ]
