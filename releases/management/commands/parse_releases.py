from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from releases.models import ChangeItem, JobRun, ReleaseSection, SourceSnapshot
from releases.parser import PARSER_VERSION, parse_release_document


class Command(BaseCommand):
    help = "Parse stored current PostgreSQL release snapshots into sections and change items."

    def add_arguments(self, parser):
        parser.add_argument("--release", action="append", dest="versions", help="Parse only this version; repeatable.")
        parser.add_argument("--force", action="store_true", help="Reparse snapshots already parsed by this parser version.")

    def handle(self, *args, **options):
        snapshots = SourceSnapshot.objects.filter(is_current=True).select_related("release").order_by("release_id")
        requested_versions = set(options["versions"] or [])
        if requested_versions:
            snapshots = snapshots.filter(release__version__in=requested_versions)
            found_versions = set(snapshots.values_list("release__version", flat=True))
            missing_versions = requested_versions - found_versions
            if missing_versions:
                raise CommandError(f"Current snapshots not found: {', '.join(sorted(missing_versions))}")

        snapshot_list = list(snapshots)
        job = JobRun.objects.create(job_type="parse_releases", discovered_count=len(snapshot_list))
        parsed_count = 0
        unchanged_count = 0
        errors = []
        section_count = 0
        item_count = 0

        for snapshot in snapshot_list:
            if not options["force"] and snapshot.parser_version == PARSER_VERSION and snapshot.sections.exists():
                unchanged_count += 1
                continue
            try:
                parsed_sections, parsed_items = parse_release_document(snapshot.raw_html)
                with transaction.atomic():
                    snapshot.sections.all().delete()
                    section_by_position = {}
                    for parsed_section in parsed_sections:
                        section = ReleaseSection.objects.create(
                            snapshot=snapshot,
                            parent=section_by_position.get(parsed_section.parent_position),
                            source_id=parsed_section.source_id,
                            title=parsed_section.title,
                            level=parsed_section.level,
                            position=parsed_section.position,
                            body_text=parsed_section.body_text,
                        )
                        section_by_position[parsed_section.position] = section
                    ChangeItem.objects.bulk_create(
                        [
                            ChangeItem(
                                snapshot=snapshot,
                                section=section_by_position[item.section_position],
                                position=item.position,
                                item_sha256=item.item_sha256,
                                text=item.text,
                                raw_html=item.raw_html,
                            )
                            for item in parsed_items
                        ]
                    )
                    snapshot.parser_version = PARSER_VERSION
                    snapshot.parsed_at = timezone.now()
                    snapshot.parse_error = ""
                    snapshot.save(update_fields=["parser_version", "parsed_at", "parse_error"])
                parsed_count += 1
                section_count += len(parsed_sections)
                item_count += len(parsed_items)
            except Exception as exc:
                snapshot.parse_error = str(exc)
                snapshot.save(update_fields=["parse_error"])
                errors.append({"version": snapshot.release.version, "error": str(exc)})
                self.stderr.write(self.style.ERROR(f"{snapshot.release.version}: {exc}"))

        job.created_count = parsed_count
        job.unchanged_count = unchanged_count
        job.failed_count = len(errors)
        job.errors = errors
        job.finished_at = timezone.now()
        if errors and parsed_count + unchanged_count:
            job.status = JobRun.Status.PARTIAL
        elif errors:
            job.status = JobRun.Status.FAILED
        else:
            job.status = JobRun.Status.SUCCESS
        job.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"status={job.status} discovered={len(snapshot_list)} parsed={parsed_count} "
                f"unchanged={unchanged_count} failed={len(errors)} sections={section_count} items={item_count}"
            )
        )
        if job.status == JobRun.Status.FAILED:
            raise CommandError("All release snapshot parsing failed")
