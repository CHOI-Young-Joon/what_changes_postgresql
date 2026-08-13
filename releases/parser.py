import hashlib
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


PARSER_VERSION = "1"
HEADING_NAMES = ("h1", "h2", "h3", "h4", "h5", "h6")
SECTION_NUMBER_PATTERN = re.compile(r"^[A-Z]\.\d+(?:\.\d+)*\.?\s*")


@dataclass
class ParsedSection:
    position: int
    parent_position: int | None
    source_id: str
    title: str
    level: int
    body_parts: list[str] = field(default_factory=list)

    @property
    def body_text(self):
        return "\n\n".join(self.body_parts)


@dataclass(frozen=True)
class ParsedItem:
    position: int
    section_position: int
    item_sha256: str
    text: str
    raw_html: str


def clean_heading(heading):
    title = heading.get_text(" ", strip=True).replace("\xa0", " ")
    title = title.removesuffix(" #").strip()
    return SECTION_NUMBER_PATTERN.sub("", title).strip()


def heading_source_id(heading):
    if heading.get("id"):
        return heading["id"]
    anchor = heading.select_one('a[href^="#"]')
    if anchor:
        return anchor.get("href", "").removeprefix("#")
    ancestor = heading.find_parent(attrs={"id": True})
    if ancestor and ancestor.get("id") != "docContent":
        return ancestor.get("id", "")
    return ""


def parse_release_document(html):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("#docContent")
    if root is None:
        raise ValueError("#docContent not found")

    headings = root.find_all(HEADING_NAMES)
    if not headings:
        raise ValueError("Release headings not found")
    minimum_heading_level = min(int(heading.name[1]) for heading in headings)

    sections = []
    items = []
    section_stack = []
    current_section = None

    for node in root.find_all((*HEADING_NAMES, "p", "li")):
        if node.name in HEADING_NAMES:
            logical_level = int(node.name[1]) - minimum_heading_level + 1
            while section_stack and section_stack[-1].level >= logical_level:
                section_stack.pop()
            section = ParsedSection(
                position=len(sections) + 1,
                parent_position=section_stack[-1].position if section_stack else None,
                source_id=heading_source_id(node),
                title=clean_heading(node),
                level=logical_level,
            )
            sections.append(section)
            section_stack.append(section)
            current_section = section
            continue

        if current_section is None:
            continue

        if node.name == "p" and node.find_parent("li") is None:
            text = node.get_text(" ", strip=True)
            if text:
                current_section.body_parts.append(text)
            continue

        if node.name == "li" and node.find_parent("li") is None:
            raw_html = str(node)
            text = node.get_text(" ", strip=True)
            if text:
                items.append(
                    ParsedItem(
                        position=len(items) + 1,
                        section_position=current_section.position,
                        item_sha256=hashlib.sha256(raw_html.encode("utf-8")).hexdigest(),
                        text=text,
                        raw_html=raw_html,
                    )
                )

    return sections, items
