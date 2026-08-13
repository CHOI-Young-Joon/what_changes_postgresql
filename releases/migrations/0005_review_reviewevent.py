import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("releases", "0004_changeitem_classification"),
    ]

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "검토 대기"), ("approved", "승인"), ("rejected", "반려")], default="pending", max_length=16)),
                ("edited_text", models.TextField(blank=True)),
                ("note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("change_item", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="review", to="releases.changeitem")),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="release_reviews", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ReviewEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(choices=[("pending", "검토 대기"), ("approved", "승인"), ("rejected", "반려")], max_length=16)),
                ("new_status", models.CharField(choices=[("pending", "검토 대기"), ("approved", "승인"), ("rejected", "반려")], max_length=16)),
                ("edited_text", models.TextField(blank=True)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="review_events", to=settings.AUTH_USER_MODEL)),
                ("review", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="releases.review")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
