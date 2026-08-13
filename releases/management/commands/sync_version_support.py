from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from releases.collector import fetch_document
from releases.models import JobRun, VersionSupport, VersionSupportSnapshot
from releases.support import VERSION_SUPPORT_URL, parse_version_support


class Command(BaseCommand):
    help = "Collect PostgreSQL version support and final release dates from the official website."

    def handle(self, *args, **options):
        job = JobRun.objects.create(job_type="sync_version_support")
        try:
            document = fetch_document(VERSION_SUPPORT_URL)
            support_rows = parse_version_support(document.html)
            relative_path = Path("postgresql") / "support" / f"{document.sha256}.html"
            absolute_path = Path(settings.BASE_DIR) / "data" / "source_snapshots" / relative_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            if not absolute_path.exists():
                absolute_path.write_bytes(document.raw_bytes)

            with transaction.atomic():
                snapshot, was_created = VersionSupportSnapshot.objects.get_or_create(
                    content_sha256=document.sha256,
                    defaults={
                        "source_url": document.url,
                        "raw_html": document.html,
                        "storage_path": str(relative_path),
                        "is_current": True,
                    },
                )
                if was_created:
                    VersionSupportSnapshot.objects.filter(is_current=True).exclude(pk=snapshot.pk).update(is_current=False)
                for row in support_rows:
                    VersionSupport.objects.update_or_create(
                        series=row.series,
                        defaults={
                            "current_minor": row.current_minor,
                            "supported": row.supported,
                            "first_release_date": row.first_release_date,
                            "final_release_date": row.final_release_date,
                            "snapshot": snapshot,
                        },
                    )

            job.status = JobRun.Status.SUCCESS
            job.discovered_count = len(support_rows)
            job.created_count = int(was_created)
            job.unchanged_count = int(not was_created)
            job.finished_at = timezone.now()
            job.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"status=success rows={len(support_rows)} snapshot={'created' if was_created else 'unchanged'}"
                )
            )
        except Exception as exc:
            job.status = JobRun.Status.FAILED
            job.failed_count = 1
            job.errors = [{"url": VERSION_SUPPORT_URL, "error": str(exc)}]
            job.finished_at = timezone.now()
            job.save()
            raise CommandError(f"Version support collection failed: {exc}") from exc
