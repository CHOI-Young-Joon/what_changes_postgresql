from pathlib import Path
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from releases.collector import (
    RELEASE_INDEX_URL,
    classify_release,
    extract_release_content,
    fetch_document,
    latest_release_per_major,
    major_number,
    parse_release_links,
)
from releases.models import JobRun, Release, SourceSnapshot


class Command(BaseCommand):
    help = "Collect PostgreSQL release pages from the official website."

    def add_arguments(self, parser):
        parser.add_argument("--release", action="append", dest="versions", help="Collect only this version; repeatable.")
        parser.add_argument("--limit", type=int, help="Limit releases after filtering; intended for validation runs.")
        parser.add_argument("--minimum-major", type=int, help="Collect releases at or above this major version.")
        parser.add_argument("--latest-majors", type=int, help="Collect only the latest release from this many newest major versions.")
        parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between release page requests.")

    def handle(self, *args, **options):
        job = JobRun.objects.create(job_type="sync_releases")
        errors = []
        created_count = 0
        unchanged_count = 0

        try:
            index_document = fetch_document(RELEASE_INDEX_URL)
            release_links = parse_release_links(index_document.html)
        except Exception as exc:
            job.status = JobRun.Status.FAILED
            job.failed_count = 1
            job.errors = [{"url": RELEASE_INDEX_URL, "error": str(exc)}]
            job.finished_at = timezone.now()
            job.save()
            raise CommandError(f"Release index collection failed: {exc}") from exc

        requested_versions = set(options["versions"] or [])
        if requested_versions:
            release_links = [item for item in release_links if item[0] in requested_versions]
            missing_versions = requested_versions - {version for version, _ in release_links}
            if missing_versions:
                job.status = JobRun.Status.FAILED
                job.failed_count = len(missing_versions)
                job.errors = [{"version": version, "error": "not present in official index"} for version in sorted(missing_versions)]
                job.finished_at = timezone.now()
                job.save()
                raise CommandError(f"Versions not present in official index: {', '.join(sorted(missing_versions))}")
        else:
            if options["minimum_major"] is not None:
                release_links = [item for item in release_links if major_number(item[0]) >= options["minimum_major"]]
            if options["latest_majors"] is not None:
                if options["latest_majors"] < 1:
                    job.status = JobRun.Status.FAILED
                    job.failed_count = 1
                    job.errors = [{"error": "--latest-majors must be at least 1"}]
                    job.finished_at = timezone.now()
                    job.save()
                    raise CommandError("--latest-majors must be at least 1")
                release_links = latest_release_per_major(release_links, options["latest_majors"])

        if options["limit"] is not None:
            if options["limit"] < 1:
                job.status = JobRun.Status.FAILED
                job.failed_count = 1
                job.errors = [{"error": "--limit must be at least 1"}]
                job.finished_at = timezone.now()
                job.save()
                raise CommandError("--limit must be at least 1")
            release_links = release_links[: options["limit"]]

        if options["delay"] < 0:
            job.status = JobRun.Status.FAILED
            job.failed_count = 1
            job.errors = [{"error": "--delay cannot be negative"}]
            job.finished_at = timezone.now()
            job.save()
            raise CommandError("--delay cannot be negative")

        job.discovered_count = len(release_links)
        job.save(update_fields=["discovered_count"])

        for index, (version, source_url) in enumerate(release_links):
            try:
                document = fetch_document(source_url)
                extracted_text, release_date = extract_release_content(document.html)
                relative_path = Path("postgresql") / "releases" / version / f"{document.sha256}.html"
                absolute_path = Path(settings.BASE_DIR) / "data" / "source_snapshots" / relative_path
                absolute_path.parent.mkdir(parents=True, exist_ok=True)
                if not absolute_path.exists():
                    absolute_path.write_bytes(document.raw_bytes)

                with transaction.atomic():
                    release, _ = Release.objects.update_or_create(
                        version=version,
                        defaults={
                            "kind": classify_release(version),
                            "release_date": release_date,
                            "source_url": document.url,
                        },
                    )
                    snapshot, was_created = SourceSnapshot.objects.get_or_create(
                        release=release,
                        content_sha256=document.sha256,
                        defaults={
                            "source_url": document.url,
                            "http_status": document.status,
                            "content_type": document.content_type,
                            "etag": document.etag,
                            "last_modified": document.last_modified,
                            "raw_html": document.html,
                            "extracted_text": extracted_text,
                            "storage_path": str(relative_path),
                            "is_current": True,
                        },
                    )
                    if was_created:
                        SourceSnapshot.objects.filter(release=release, is_current=True).exclude(pk=snapshot.pk).update(is_current=False)
                        created_count += 1
                    else:
                        unchanged_count += 1
            except Exception as exc:
                errors.append({"version": version, "url": source_url, "error": str(exc)})
                self.stderr.write(self.style.ERROR(f"{version}: {exc}"))
            if index + 1 < len(release_links) and options["delay"]:
                sleep(options["delay"])

        job.created_count = created_count
        job.unchanged_count = unchanged_count
        job.failed_count = len(errors)
        job.errors = errors
        job.finished_at = timezone.now()
        if errors and created_count + unchanged_count:
            job.status = JobRun.Status.PARTIAL
        elif errors:
            job.status = JobRun.Status.FAILED
        else:
            job.status = JobRun.Status.SUCCESS
        job.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"status={job.status} discovered={job.discovered_count} "
                f"created={created_count} unchanged={unchanged_count} failed={len(errors)}"
            )
        )

        if job.status == JobRun.Status.FAILED:
            raise CommandError("All release page collections failed")
