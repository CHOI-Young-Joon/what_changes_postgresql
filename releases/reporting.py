from dataclasses import dataclass
from html import escape

from django.utils import timezone

from releases.comparison import build_comparison_summary
from releases.models import ChangeItem, Release, Review, SourceSnapshot


@dataclass(frozen=True)
class ReportItem:
    version: str
    change_type: str
    area: str
    text: str
    source_url: str


def build_approved_report(from_version, to_version, level):
    if level not in ("customer", "dba"):
        raise ValueError("Report level must be customer or dba")
    summary = build_comparison_summary(from_version, to_version)
    release_ids = Release.objects.filter(version__in=summary["included_releases"]).values_list("id", flat=True)
    snapshot_ids = SourceSnapshot.objects.filter(is_current=True, release_id__in=release_ids).values_list("id", flat=True)
    queryset = (
        ChangeItem.objects.filter(snapshot_id__in=snapshot_ids, review__status=Review.Status.APPROVED)
        .select_related("snapshot__release", "section", "review")
        .order_by("snapshot__release__release_date", "snapshot__release_id", "position")
    )
    items = [
        ReportItem(
            version=item.snapshot.release.version,
            change_type=item.get_change_type_display(),
            area=item.section.title,
            text=item.review.edited_text or item.text,
            source_url=item.snapshot.source_url + (f"#{item.section.source_id}" if item.section.source_id else ""),
        )
        for item in queryset
    ]
    if not items:
        raise ValueError("No approved change items exist in this comparison range")
    return {
        "title": "PostgreSQL Upgrade Brief",
        "level": level,
        "generated_at": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "summary": summary,
        "items": items,
    }


def support_line(label, support):
    if support is None:
        return f"{label}: 공식 지원정보 없음"
    state = "지원 중" if support["supported"] else "지원 종료"
    return f"{label}: PostgreSQL {support['series']} {state}, 최종 지원일 {support['final_release_date']}"


def render_text(report):
    summary = report["summary"]
    lines = [
        report["title"],
        "=" * len(report["title"]),
        f"보고서 수준: {'고객용' if report['level'] == 'customer' else 'DBA용'}",
        f"생성시각: {report['generated_at']}",
        f"업그레이드 범위: {summary['from_version']} (제외) → {summary['to_version']} (포함)",
        f"포함 릴리스: {summary['release_count']}개 / 승인 항목: {len(report['items'])}개",
        support_line("AS-IS", summary["from_support"]),
        support_line("TO-BE", summary["to_support"]),
        "",
    ]
    for index, item in enumerate(report["items"], 1):
        lines.extend([f"{index}. PostgreSQL {item.version} · {item.area} · {item.change_type}", item.text, f"공식 원문: {item.source_url}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(report):
    summary = report["summary"]
    lines = [
        f"# {report['title']}", "",
        f"- 보고서 수준: **{'고객용' if report['level'] == 'customer' else 'DBA용'}**",
        f"- 생성시각: {report['generated_at']}",
        f"- 업그레이드 범위: **{summary['from_version']}** (제외) → **{summary['to_version']}** (포함)",
        f"- 포함 릴리스: {summary['release_count']}개",
        f"- 승인 항목: {len(report['items'])}개",
        f"- {support_line('AS-IS', summary['from_support'])}",
        f"- {support_line('TO-BE', summary['to_support'])}", "", "## 승인된 변경사항", "",
    ]
    for item in report["items"]:
        lines.extend([f"### PostgreSQL {item.version} · {item.area}", "", f"**유형:** {item.change_type}", "", item.text, "", f"[PostgreSQL 공식 원문]({item.source_url})", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_html(report):
    summary = report["summary"]
    items_html = "".join(
        "<article>" f"<h2>PostgreSQL {escape(item.version)} · {escape(item.area)}</h2>" f"<p><strong>유형:</strong> {escape(item.change_type)}</p>" f"<p>{escape(item.text).replace(chr(10), '<br>')}</p>" f'<p><a href="{escape(item.source_url, quote=True)}">PostgreSQL 공식 원문</a></p>' "</article>"
        for item in report["items"]
    )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>PostgreSQL Upgrade Brief</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;color:#18251f;font:16px/1.65 system-ui,sans-serif}"
        "h1,h2{font-family:Georgia,serif}article{border-top:1px solid #dbe4df;padding:18px 0}a{color:#176b4d}</style></head><body>"
        f"<h1>{escape(report['title'])}</h1><p><strong>업그레이드 범위:</strong> {escape(summary['from_version'])} (제외) → {escape(summary['to_version'])} (포함)<br>"
        f"<strong>포함 릴리스:</strong> {summary['release_count']}개 · <strong>승인 항목:</strong> {len(report['items'])}개<br>"
        f"{escape(support_line('AS-IS', summary['from_support']))}<br>{escape(support_line('TO-BE', summary['to_support']))}</p>{items_html}</body></html>"
    )
