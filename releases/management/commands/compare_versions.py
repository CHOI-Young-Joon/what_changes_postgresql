import json

from django.core.management.base import BaseCommand, CommandError

from releases.comparison import build_comparison_summary


class Command(BaseCommand):
    help = "Calculate the collected release-note range between PostgreSQL AS-IS and TO-BE versions."

    def add_arguments(self, parser):
        parser.add_argument("--from-version", required=True, help="Current PostgreSQL version (excluded).")
        parser.add_argument("--to-version", required=True, help="Target PostgreSQL version (included).")
        parser.add_argument("--json", action="store_true", help="Output the complete summary as JSON.")
        parser.add_argument("--include-prereleases", action="store_true", help="Include beta and RC releases in the range.")

    def handle(self, *args, **options):
        try:
            summary = build_comparison_summary(
                options["from_version"],
                options["to_version"],
                include_prereleases=options["include_prereleases"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
            return

        self.stdout.write(f"AS-IS: {summary['from_version']} (excluded)")
        self.stdout.write(f"TO-BE: {summary['to_version']} (included)")
        self.stdout.write(f"Included releases: {summary['release_count']}")
        self.stdout.write(f"Major releases: {summary['major_release_count']} ({', '.join(summary['major_releases'])})")
        self.stdout.write(f"Minor releases: {summary['minor_release_count']}")
        self.stdout.write(f"Prereleases: {summary['prerelease_count']}")
        self.stdout.write(f"Sections: {summary['section_count']}")
        self.stdout.write(f"Change items: {summary['change_item_count']}")
        self.stdout.write(
            "Change type candidates: "
            + ", ".join(f"{change_type}={count}" for change_type, count in summary["change_type_counts"].items())
        )
        for label, support in (("AS-IS support", summary["from_support"]), ("TO-BE support", summary["to_support"])):
            if support is None:
                self.stdout.write(f"{label}: no official support data")
            else:
                state = "supported" if support["supported"] else "unsupported"
                self.stdout.write(f"{label}: {state}, final release {support['final_release_date']}")
