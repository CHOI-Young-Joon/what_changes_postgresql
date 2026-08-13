from django.core.management.base import BaseCommand

from releases.models import ChangeItem, SourceSnapshot
from releases.parser import PARSER_VERSION, extract_item_text


class Command(BaseCommand):
    help = "Upgrade stored item text to parser v2 without replacing item IDs or review history."

    def handle(self, *args, **options):
        changed = []
        for item in ChangeItem.objects.all().iterator(chunk_size=1000):
            cleaned_text = extract_item_text(item.raw_html)
            if cleaned_text != item.text or item.classification_version:
                item.text = cleaned_text
                item.classification_version = ""
                changed.append(item)
            if len(changed) >= 1000:
                ChangeItem.objects.bulk_update(changed, ["text", "classification_version"], batch_size=1000)
                changed.clear()
        if changed:
            ChangeItem.objects.bulk_update(changed, ["text", "classification_version"], batch_size=1000)

        snapshot_count = SourceSnapshot.objects.filter(is_current=True).update(parser_version=PARSER_VERSION)
        self.stdout.write(self.style.SUCCESS(f"parser_version={PARSER_VERSION} snapshots={snapshot_count}"))
