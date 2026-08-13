from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("releases", "0003_versionsupportsnapshot_versionsupport")]

    operations = [
        migrations.AddField(model_name="changeitem", name="change_type", field=models.CharField(choices=[("added", "Added"), ("changed", "Changed"), ("deprecated", "Deprecated"), ("removed", "Removed"), ("fixed", "Fixed"), ("security", "Security"), ("other", "Other")], default="other", max_length=16)),
        migrations.AddField(model_name="changeitem", name="classification_rule", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="changeitem", name="classification_version", field=models.CharField(blank=True, max_length=32)),
    ]
