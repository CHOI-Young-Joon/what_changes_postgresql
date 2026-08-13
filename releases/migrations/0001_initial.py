import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="JobRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_type", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("running", "Running"), ("success", "Success"), ("partial", "Partial"), ("failed", "Failed")], default="running", max_length=16)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("discovered_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("unchanged_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="Release",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=32, unique=True)),
                ("kind", models.CharField(choices=[("major", "Major"), ("minor", "Minor"), ("beta", "Beta"), ("rc", "Release candidate")], max_length=16)),
                ("release_date", models.DateField(blank=True, null=True)),
                ("source_url", models.URLField(max_length=500)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-release_date", "-id"]},
        ),
        migrations.CreateModel(
            name="SourceSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_url", models.URLField(max_length=500)),
                ("http_status", models.PositiveSmallIntegerField(default=200)),
                ("content_type", models.CharField(blank=True, max_length=200)),
                ("etag", models.CharField(blank=True, max_length=500)),
                ("last_modified", models.CharField(blank=True, max_length=200)),
                ("content_sha256", models.CharField(max_length=64)),
                ("raw_html", models.TextField()),
                ("extracted_text", models.TextField()),
                ("storage_path", models.CharField(max_length=500)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
                ("is_current", models.BooleanField(default=True)),
                ("release", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="releases.release")),
            ],
            options={"ordering": ["-fetched_at"]},
        ),
        migrations.AddConstraint(
            model_name="sourcesnapshot",
            constraint=models.UniqueConstraint(fields=("release", "content_sha256"), name="unique_release_snapshot_content"),
        ),
    ]
