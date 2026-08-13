import hashlib
import json

from django.core.management.base import BaseCommand, CommandError

from releases.comparison import build_comparison_summary
from releases.models import ChangeItem, Release, SourceSnapshot
from releases.parser import PARSER_VERSION, extract_item_text


DEFAULT_RANGES = (
    ("9.2.10", "18.4"),
    ("12.0", "16.0"),
    ("14.0", "18.0"),
    ("17.0", "18.0"),
    ("18.3", "18.4"),
)


class Command(BaseCommand):
    help = "Validate representative PostgreSQL upgrade ranges against structured official source data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--range",
            action="append",
            dest="ranges",
            default=[],
            metavar="FROM:TO",
            help="Range to validate; repeatable. Defaults to the five project pilot ranges.",
        )

    @staticmethod
    def parse_range(value):
        parts = value.split(":", 1)
        if len(parts) != 2 or not all(parts):
            raise CommandError(f"Invalid range {value!r}; expected FROM:TO")
        return tuple(parts)

    def handle(self, *args, **options):
        ranges = [self.parse_range(value) for value in options["ranges"]] or list(DEFAULT_RANGES)
        results = []
        all_errors = []

        for from_version, to_version in ranges:
            try:
                summary = build_comparison_summary(from_version, to_version)
            except ValueError as exc:
                all_errors.append(f"{from_version}->{to_version}: {exc}")
                continue

            release_ids = list(
                Release.objects.filter(version__in=summary["included_releases"]).values_list("id", flat=True)
            )
            snapshots = SourceSnapshot.objects.filter(is_current=True, release_id__in=release_ids)
            items = ChangeItem.objects.filter(snapshot__in=snapshots).select_related("snapshot")
            errors = []

            if snapshots.count() != summary["release_count"]:
                errors.append("current snapshot count differs from included release count")
            if items.count() != summary["change_item_count"]:
                errors.append("change item count differs from comparison summary")
            if snapshots.exclude(parser_version=PARSER_VERSION).exists():
                errors.append(f"one or more snapshots are not parser version {PARSER_VERSION}")
            if snapshots.exclude(source_url__startswith="https://www.postgresql.org/docs/release/").exists():
                errors.append("one or more snapshot URLs are not official PostgreSQL release URLs")

            for item in items.iterator(chunk_size=1000):
                expected_sha = hashlib.sha256(item.raw_html.encode("utf-8")).hexdigest()
                if item.item_sha256 != expected_sha:
                    errors.append(f"item {item.pk} raw HTML SHA-256 mismatch")
                    break
                if item.text != extract_item_text(item.raw_html):
                    errors.append(f"item {item.pk} structured text differs from raw HTML")
                    break
                if "§" in item.text:
                    errors.append(f"item {item.pk} contains a commit marker")
                    break

            result = {
                "from_version": from_version,
                "to_version": to_version,
                "release_count": summary["release_count"],
                "major_release_count": summary["major_release_count"],
                "minor_release_count": summary["minor_release_count"],
                "section_count": summary["section_count"],
                "change_item_count": summary["change_item_count"],
                "errors": errors,
            }
            results.append(result)
            all_errors.extend(f"{from_version}->{to_version}: {error}" for error in errors)

        payload = {"status": "failed" if all_errors else "success", "ranges": results, "errors": all_errors}
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        if all_errors:
            raise CommandError("Pilot range validation failed")
