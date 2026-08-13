import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from releases.models import Release, SourceSnapshot


class Command(BaseCommand):
    help = "Verify database snapshot metadata against stored official HTML files."

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR) / "data" / "source_snapshots"
        snapshots = list(SourceSnapshot.objects.select_related("release"))
        missing_files = []
        hash_mismatches = []
        total_file_bytes = 0

        for snapshot in snapshots:
            file_path = root / snapshot.storage_path
            if not file_path.is_file():
                missing_files.append(snapshot.release.version)
                continue
            payload = file_path.read_bytes()
            total_file_bytes += len(payload)
            if hashlib.sha256(payload).hexdigest() != snapshot.content_sha256:
                hash_mismatches.append(snapshot.release.version)

        duplicate_current = list(
            SourceSnapshot.objects.filter(is_current=True)
            .values("release_id")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        result = {
            "releases": Release.objects.count(),
            "snapshots": len(snapshots),
            "current_snapshots": SourceSnapshot.objects.filter(is_current=True).count(),
            "missing_files": missing_files,
            "hash_mismatches": hash_mismatches,
            "duplicate_current": duplicate_current,
            "missing_dates": Release.objects.filter(release_date__isnull=True).count(),
            "total_file_bytes": total_file_bytes,
        }
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))

        if missing_files or hash_mismatches or duplicate_current:
            raise CommandError("Snapshot verification failed")
