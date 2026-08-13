from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .collector import (
    classify_release,
    extract_release_content,
    latest_release_per_major,
    major_number,
    parse_release_links,
    require_official_url,
)
from .parser import parse_release_document
from .collector import FetchedDocument, RELEASE_INDEX_URL
from .comparison import PostgreSQLVersion, versions_in_upgrade_range
from .classifier import classify_change
from .support import parse_version_support
from .models import JobRun, Release, SourceSnapshot


class CollectorParsingTests(SimpleTestCase):
    def test_release_links_are_unique_and_ordered(self):
        html = '<a href="/docs/release/18.4/">18.4</a><a href="/docs/release/18.4/">duplicate</a><a href="/docs/release/17.0/">17</a>'
        self.assertEqual(
            parse_release_links(html),
            [
                ("18.4", "https://www.postgresql.org/docs/release/18.4/"),
                ("17.0", "https://www.postgresql.org/docs/release/17.0/"),
            ],
        )

    def test_release_date_and_text_are_extracted(self):
        text, release_date = extract_release_content("<main><p><strong>Release date:&nbsp;</strong>2026-05-14</p><p>Fix one.</p></main>")
        self.assertEqual(str(release_date), "2026-05-14")
        self.assertIn("Fix one.", text)

    def test_release_kind_rules(self):
        self.assertEqual(classify_release("18.0"), "major")
        self.assertEqual(classify_release("18.4"), "minor")
        self.assertEqual(classify_release("9.2.0"), "major")
        self.assertEqual(classify_release("9.2.10"), "minor")
        self.assertEqual(classify_release("19beta2"), "beta")
        self.assertEqual(classify_release("19rc1"), "rc")

    def test_non_official_url_is_rejected(self):
        with self.assertRaises(ValueError):
            require_official_url("https://example.com/docs/release/")

    def test_latest_release_from_each_newest_major_is_selected(self):
        links = [("18.4", "a"), ("18.3", "b"), ("17.10", "c"), ("17.9", "d"), ("16.14", "e")]
        self.assertEqual(latest_release_per_major(links, 2), [("18.4", "a"), ("17.10", "c")])
        self.assertEqual(major_number("9.2.10"), 9)


class ReleaseDocumentParsingTests(SimpleTestCase):
    def test_heading_levels_body_and_top_level_items_are_parsed(self):
        html = """
            <div id="docContent">
              <div id="RELEASE-18"><h2>E.1. Release 18 <a href="#RELEASE-18">#</a></h2></div>
              <p>Release date: 2025-09-25</p>
              <div id="RELEASE-18-CHANGES"><h3>E.1.1. Changes <a href="#RELEASE-18-CHANGES">#</a></h3></div>
              <p>Section introduction.</p>
              <ul><li><p>First change.</p><ul><li>Nested detail.</li></ul></li><li>Second change.</li></ul>
            </div>
        """
        sections, items = parse_release_document(html)

        self.assertEqual([(section.title, section.level, section.parent_position) for section in sections], [("Release 18", 1, None), ("Changes", 2, 1)])
        self.assertIn("Section introduction.", sections[1].body_text)
        self.assertEqual(len(items), 2)
        self.assertIn("Nested detail.", items[0].text)


class PostgreSQLVersionComparisonTests(SimpleTestCase):
    def test_pre_10_and_post_10_versions_sort_correctly(self):
        values = ["18.4", "9.2.10", "10.0", "9.2.11", "17.10"]
        ordered = [version.value for version in sorted(PostgreSQLVersion.parse(value) for value in values)]
        self.assertEqual(ordered, ["9.2.10", "9.2.11", "10.0", "17.10", "18.4"])

    def test_prereleases_sort_before_initial_stable_release(self):
        values = ["19.0", "19rc1", "19beta2", "19beta1"]
        ordered = [version.value for version in sorted(PostgreSQLVersion.parse(value) for value in values)]
        self.assertEqual(ordered, ["19beta1", "19beta2", "19rc1", "19.0"])

    def test_range_excludes_from_and_includes_to(self):
        available = ["9.2.10", "9.2.11", "9.3.0", "10.0", "10.1"]
        self.assertEqual(
            versions_in_upgrade_range(available, "9.2.10", "10.0"),
            ["9.2.11", "9.3.0", "10.0"],
        )

    def test_reverse_or_unknown_range_is_rejected(self):
        with self.assertRaises(ValueError):
            versions_in_upgrade_range(["17.0", "18.0"], "18.0", "17.0")
        with self.assertRaises(ValueError):
            versions_in_upgrade_range(["17.0", "18.0"], "16.0", "18.0")

    def test_prereleases_are_excluded_by_default_and_can_be_included(self):
        available = ["18.0", "19beta1", "19rc1", "19.0"]
        self.assertEqual(versions_in_upgrade_range(available, "18.0", "19.0"), ["19.0"])
        self.assertEqual(
            versions_in_upgrade_range(available, "18.0", "19.0", include_prereleases=True),
            ["19beta1", "19rc1", "19.0"],
        )
        with self.assertRaises(ValueError):
            versions_in_upgrade_range(available, "18.0", "19rc1")


class VersionSupportParsingTests(SimpleTestCase):
    def test_official_support_table_is_parsed(self):
        html = """
          <table><thead><tr><th>Version</th><th>Current minor</th><th>Supported</th><th>First Release</th><th>Final Release</th></tr></thead>
          <tbody><tr><td>18</td><td>18.4</td><td>Yes</td><td>September 25, 2025</td><td>November 14, 2030</td></tr>
          <tr><td>13</td><td>13.23</td><td>No</td><td>September 24, 2020</td><td>November 13, 2025</td></tr></tbody></table>
        """
        rows = parse_version_support(html)
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].supported)
        self.assertEqual(str(rows[0].final_release_date), "2030-11-14")
        self.assertFalse(rows[1].supported)


class ChangeClassificationTests(SimpleTestCase):
    def test_explicit_change_language_is_classified(self):
        cases = {
            "Add support for a new data type": "added",
            "Remove obsolete server parameter": "removed",
            "Deprecate the old function": "deprecated",
            "Fix incorrect query results": "fixed",
            "Improve planner behavior": "changed",
            "Repair security vulnerability CVE-2026-1234": "security",
            "Documentation wording only": "other",
            "Fix failure to remove non-first table segments": "fixed",
            "Fix visibility of obsolete row versions": "fixed",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(classify_change(text).change_type, expected)


class ReleaseSyncCommandTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.base_dir = Path(self.temporary_directory.name)
        self.index_document = self.document(
            RELEASE_INDEX_URL,
            '<div id="docContent"><a href="/docs/release/18.4/">18.4</a><a href="/docs/release/17.10/">17.10</a></div>',
        )

    @staticmethod
    def document(url, html):
        return FetchedDocument(
            url=url,
            status=200,
            content_type="text/html; charset=utf-8",
            etag="",
            last_modified="",
            raw_bytes=html.encode("utf-8"),
        )

    def release_document(self, version, change_text):
        return self.document(
            f"https://www.postgresql.org/docs/release/{version}/",
            f'<div id="docContent"><h1>Release {version}</h1><p><strong>Release date:</strong>2026-05-14</p><h2>Changes</h2><ul><li>{change_text}</li></ul></div>',
        )

    def test_changed_source_creates_new_current_snapshot_and_preserves_previous(self):
        current_document = self.release_document("18.4", "First content")
        changed_document = self.release_document("18.4", "Changed content")

        with self.settings(BASE_DIR=self.base_dir):
            with patch("releases.management.commands.sync_releases.fetch_document", side_effect=[self.index_document, current_document]):
                call_command("sync_releases", "--release", "18.4", "--delay", "0")
            with patch("releases.management.commands.sync_releases.fetch_document", side_effect=[self.index_document, changed_document]):
                call_command("sync_releases", "--release", "18.4", "--delay", "0")

        release = Release.objects.get(version="18.4")
        self.assertEqual(release.snapshots.count(), 2)
        self.assertEqual(release.snapshots.filter(is_current=True).count(), 1)
        self.assertIn("Changed content", release.snapshots.get(is_current=True).raw_html)
        self.assertEqual(len(list((self.base_dir / "data" / "source_snapshots").rglob("*.html"))), 2)

    def test_one_release_failure_is_isolated_as_partial_job(self):
        good_document = self.release_document("18.4", "Good content")

        def fetch_side_effect(url):
            if url == RELEASE_INDEX_URL:
                return self.index_document
            if url.endswith("/18.4/"):
                return good_document
            raise URLError("isolated test failure")

        with self.settings(BASE_DIR=self.base_dir):
            with patch("releases.management.commands.sync_releases.fetch_document", side_effect=fetch_side_effect):
                call_command("sync_releases", "--release", "18.4", "--release", "17.10", "--delay", "0")

        job = JobRun.objects.get(job_type="sync_releases")
        self.assertEqual(job.status, JobRun.Status.PARTIAL)
        self.assertEqual(job.created_count, 1)
        self.assertEqual(job.failed_count, 1)
        self.assertTrue(SourceSnapshot.objects.filter(release__version="18.4").exists())
        self.assertFalse(SourceSnapshot.objects.filter(release__version="17.10").exists())
