from django.test import SimpleTestCase

from .collector import (
    classify_release,
    extract_release_content,
    latest_release_per_major,
    major_number,
    parse_release_links,
    require_official_url,
)


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
