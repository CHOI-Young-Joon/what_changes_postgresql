from django.core.management.base import BaseCommand
from django.utils import timezone

from releases.classifier import CLASSIFIER_VERSION, classify_change
from releases.models import ChangeItem, JobRun


class Command(BaseCommand):
    help = "Assign review-candidate change types using deterministic English source-text rules."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reclassify items already processed by this rule version.")

    def handle(self, *args, **options):
        items = ChangeItem.objects.all()
        if not options["force"]:
            items = items.exclude(classification_version=CLASSIFIER_VERSION)
        item_list = list(items)
        job = JobRun.objects.create(job_type="classify_changes", discovered_count=len(item_list))

        changed_count = 0
        unchanged_count = 0
        for item in item_list:
            classification = classify_change(item.text)
            if item.change_type == classification.change_type and item.classification_rule == classification.rule:
                unchanged_count += 1
            else:
                changed_count += 1
            item.change_type = classification.change_type
            item.classification_rule = classification.rule
            item.classification_version = CLASSIFIER_VERSION

        if item_list:
            ChangeItem.objects.bulk_update(
                item_list,
                ["change_type", "classification_rule", "classification_version"],
                batch_size=1000,
            )

        job.status = JobRun.Status.SUCCESS
        job.created_count = changed_count
        job.unchanged_count = unchanged_count
        job.finished_at = timezone.now()
        job.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"status=success discovered={len(item_list)} changed={changed_count} unchanged={unchanged_count}"
            )
        )
