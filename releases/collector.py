import hashlib
import re
import time
from dataclasses import dataclass
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


OFFICIAL_HOST = "www.postgresql.org"
RELEASE_INDEX_URL = "https://www.postgresql.org/docs/release/"
RELEASE_PATH_PATTERN = re.compile(r"^/docs/release/([^/]+)/$")
RELEASE_DATE_PATTERN = re.compile(r"Release date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
MAJOR_NUMBER_PATTERN = re.compile(r"^(\d+)")
USER_AGENT = "PostgreSQL-Upgrade-Brief-Collector/0.1 (+internal documentation tool)"


@dataclass(frozen=True)
class FetchedDocument:
    url: str
    status: int
    content_type: str
    etag: str
    last_modified: str
    raw_bytes: bytes

    @property
    def sha256(self):
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def html(self):
        return self.raw_bytes.decode("utf-8", errors="replace")


def require_official_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise ValueError(f"Official PostgreSQL HTTPS URL required: {url}")


def fetch_document(url, timeout=30, attempts=3):
    require_official_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                final_url = response.geturl()
                require_official_url(final_url)
                return FetchedDocument(
                    url=final_url,
                    status=response.status,
                    content_type=response.headers.get("Content-Type", ""),
                    etag=response.headers.get("ETag", ""),
                    last_modified=response.headers.get("Last-Modified", ""),
                    raw_bytes=response.read(),
                )
        except HTTPError as exc:
            if exc.code < 500 or attempt == attempts:
                raise
        except (TimeoutError, URLError):
            if attempt == attempts:
                raise
        time.sleep(2 ** (attempt - 1))


def parse_release_links(html):
    soup = BeautifulSoup(html, "html.parser")
    releases = []
    seen = set()
    for anchor in soup.select('a[href^="/docs/release/"]'):
        href = anchor.get("href", "")
        match = RELEASE_PATH_PATTERN.match(href)
        if not match:
            continue
        version = match.group(1)
        if version in seen:
            continue
        seen.add(version)
        releases.append((version, urljoin(RELEASE_INDEX_URL, href)))
    return releases


def extract_release_content(html):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main") or soup.select_one("#docContent") or soup.body or soup
    text = main.get_text("\n", strip=True)
    date_match = RELEASE_DATE_PATTERN.search(text.replace("\xa0", " "))
    release_date = date.fromisoformat(date_match.group(1)) if date_match else None
    return text, release_date


def classify_release(version):
    lower_version = version.lower()
    if "beta" in lower_version:
        return "beta"
    if "rc" in lower_version:
        return "rc"

    numeric_parts = [int(part) for part in version.split(".") if part.isdigit()]
    if not numeric_parts:
        return "minor"
    if numeric_parts[0] >= 10:
        return "major" if len(numeric_parts) == 1 or numeric_parts[1:] == [0] else "minor"
    return "major" if numeric_parts[-1] == 0 else "minor"


def major_number(version):
    match = MAJOR_NUMBER_PATTERN.match(version)
    if not match:
        raise ValueError(f"Cannot determine major version: {version}")
    return int(match.group(1))


def latest_release_per_major(release_links, major_count):
    selected = []
    seen_majors = set()
    for release_link in release_links:
        release_major = major_number(release_link[0])
        if release_major in seen_majors:
            continue
        if len(seen_majors) >= major_count:
            break
        seen_majors.add(release_major)
        selected.append(release_link)
    return selected
