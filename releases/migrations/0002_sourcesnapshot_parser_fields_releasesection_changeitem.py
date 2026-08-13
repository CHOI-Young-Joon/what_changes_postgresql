import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("releases", "0001_initial")]

    operations = [
        migrations.AddField(model_name="sourcesnapshot", name="parse_error", field=models.TextField(blank=True)),
        migrations.AddField(model_name="sourcesnapshot", name="parsed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="sourcesnapshot", name="parser_version", field=models.CharField(blank=True, max_length=32)),
        migrations.CreateModel(
            name="ReleaseSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_id", models.CharField(blank=True, max_length=200)),
                ("title", models.CharField(max_length=500)),
                ("level", models.PositiveSmallIntegerField()),
                ("position", models.PositiveIntegerField()),
                ("body_text", models.TextField(blank=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="releases.releasesection")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="releases.sourcesnapshot")),
            ],
            options={"ordering": ["position"]},
        ),
        migrations.CreateModel(
            name="ChangeItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField()),
                ("item_sha256", models.CharField(max_length=64)),
                ("text", models.TextField()),
                ("raw_html", models.TextField()),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="change_items", to="releases.releasesection")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="change_items", to="releases.sourcesnapshot")),
            ],
            options={"ordering": ["position"]},
        ),
        migrations.AddConstraint(model_name="releasesection", constraint=models.UniqueConstraint(fields=("snapshot", "position"), name="unique_snapshot_section_position")),
        migrations.AddConstraint(model_name="changeitem", constraint=models.UniqueConstraint(fields=("snapshot", "position"), name="unique_snapshot_change_position")),
    ]
