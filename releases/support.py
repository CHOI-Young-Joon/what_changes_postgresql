from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup


VERSION_SUPPORT_URL = "https://www.postgresql.org/support/versioning/"
EXPECTED_HEADERS = ["Version", "Current minor", "Supported", "First Release", "Final Release"]


@dataclass(frozen=True)
class ParsedVersionSupport:
    series: str
    current_minor: str
    supported: bool
    first_release_date: object
    final_release_date: object


def parse_version_support(html):
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        headers = [header.get_text(" ", strip=True) for header in table.select("thead th")]
        if headers != EXPECTED_HEADERS:
            continue
        rows = []
        for row in table.select("tbody tr"):
            values = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if len(values) != len(EXPECTED_HEADERS):
                continue
            rows.append(
                ParsedVersionSupport(
                    series=values[0],
                    current_minor=values[1],
                    supported=values[2].lower() == "yes",
                    first_release_date=datetime.strptime(values[3], "%B %d, %Y").date(),
                    final_release_date=datetime.strptime(values[4], "%B %d, %Y").date(),
                )
            )
        if rows:
            return rows
    raise ValueError("PostgreSQL version support table not found")
