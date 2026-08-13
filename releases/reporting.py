from dataclasses import dataclass
from base64 import b64encode
from html import escape
from pathlib import Path

from django.utils import timezone

from releases.comparison import build_comparison_summary
from releases.models import ChangeItem, Release, ReportProfile, Review, SourceSnapshot


REPORT_LIMITATIONS = (
    "이 보고서는 PostgreSQL 공식 릴리스 노트를 구조화한 자료이며 개별 시스템의 호환성 시험 결과가 아닙니다.",
    "사용 중인 확장 모듈, 드라이버, 운영체제, 애플리케이션 SQL과 설정의 호환성은 별도로 검증해야 합니다.",
    "운영 적용 전 백업·복구와 실제 데이터 기반 업그레이드 리허설을 수행해야 합니다.",
)


@dataclass(frozen=True)
class ReportItem:
    version: str
    change_type: str
    area: str
    text: str
    source_url: str


def build_branding(profile_id):
    if not profile_id:
        return {"profile_id": None, "customer_name": "", "project_name": "", "logo_path": "", "logo_mime": ""}
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid report profile") from exc
    profile = ReportProfile.objects.filter(pk=profile_id, is_active=True).first()
    if profile is None:
        raise ValueError("Report profile does not exist or is inactive")
    logo_path = ""
    logo_mime = ""
    if profile.logo:
        candidate = Path(profile.logo.path)
        if not candidate.is_file():
            raise ValueError("Report profile logo file is missing")
        logo_path = str(candidate)
        logo_mime = "image/png" if candidate.suffix.lower() == ".png" else "image/jpeg"
    return {
        "profile_id": profile.pk,
        "customer_name": profile.customer_name,
        "project_name": profile.project_name,
        "logo_path": logo_path,
        "logo_mime": logo_mime,
    }


def build_approved_report(from_version, to_version, level, profile_id=None):
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
        "branding": build_branding(profile_id),
        "limitations": REPORT_LIMITATIONS,
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
    branding = report["branding"]
    lines = [
        report["title"],
        "=" * len(report["title"]),
        f"보고서 수준: {'고객용' if report['level'] == 'customer' else 'DBA용'}",
        f"생성시각: {report['generated_at']}",
        *([f"고객명: {branding['customer_name']}"] if branding["customer_name"] else []),
        *([f"프로젝트명: {branding['project_name']}"] if branding["project_name"] else []),
        f"업그레이드 범위: {summary['from_version']} (제외) → {summary['to_version']} (포함)",
        f"포함 릴리스: {summary['release_count']}개 / 승인 항목: {len(report['items'])}개",
        support_line("AS-IS", summary["from_support"]),
        support_line("TO-BE", summary["to_support"]),
        "",
        "적용 전 확인사항",
        *[f"{index}. {limitation}" for index, limitation in enumerate(report["limitations"], 1)],
        "",
    ]
    for index, item in enumerate(report["items"], 1):
        lines.extend([f"{index}. PostgreSQL {item.version} · {item.area} · {item.change_type}", item.text, f"공식 원문: {item.source_url}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(report):
    summary = report["summary"]
    branding = report["branding"]
    lines = [
        f"# {report['title']}", "",
        f"- 보고서 수준: **{'고객용' if report['level'] == 'customer' else 'DBA용'}**",
        f"- 생성시각: {report['generated_at']}",
        *([f"- 고객명: **{branding['customer_name']}**"] if branding["customer_name"] else []),
        *([f"- 프로젝트명: **{branding['project_name']}**"] if branding["project_name"] else []),
        f"- 업그레이드 범위: **{summary['from_version']}** (제외) → **{summary['to_version']}** (포함)",
        f"- 포함 릴리스: {summary['release_count']}개",
        f"- 승인 항목: {len(report['items'])}개",
        f"- {support_line('AS-IS', summary['from_support'])}",
        f"- {support_line('TO-BE', summary['to_support'])}", "", "## 적용 전 확인사항", "",
        *[f"- {limitation}" for limitation in report["limitations"]],
        "", "## 승인된 변경사항", "",
    ]
    for item in report["items"]:
        lines.extend([f"### PostgreSQL {item.version} · {item.area}", "", f"**유형:** {item.change_type}", "", item.text, "", f"[PostgreSQL 공식 원문]({item.source_url})", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_html(report):
    summary = report["summary"]
    branding = report["branding"]
    logo_html = ""
    if branding["logo_path"]:
        logo_data = b64encode(Path(branding["logo_path"]).read_bytes()).decode("ascii")
        logo_html = f'<img src="data:{branding["logo_mime"]};base64,{logo_data}" alt="{escape(branding["customer_name"])} 로고" style="max-width:180px;max-height:72px;object-fit:contain">'
    branding_html = "".join(
        part
        for part in (
            f"<br><strong>고객명:</strong> {escape(branding['customer_name'])}" if branding["customer_name"] else "",
            f"<br><strong>프로젝트명:</strong> {escape(branding['project_name'])}" if branding["project_name"] else "",
        )
    )
    limitations_html = "".join(f"<li>{escape(limitation)}</li>" for limitation in report["limitations"])
    items_html = "".join(
        "<article>" f"<h2>PostgreSQL {escape(item.version)} · {escape(item.area)}</h2>" f"<p><strong>유형:</strong> {escape(item.change_type)}</p>" f"<p>{escape(item.text).replace(chr(10), '<br>')}</p>" f'<p><a href="{escape(item.source_url, quote=True)}">PostgreSQL 공식 원문</a></p>' "</article>"
        for item in report["items"]
    )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>PostgreSQL Upgrade Brief</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;color:#18251f;font:16px/1.65 system-ui,sans-serif}"
        "h1,h2{font-family:Georgia,serif}article{border-top:1px solid #dbe4df;padding:18px 0}a{color:#176b4d}</style></head><body>"
        f"{logo_html}<h1>{escape(report['title'])}</h1><p><strong>업그레이드 범위:</strong> {escape(summary['from_version'])} (제외) → {escape(summary['to_version'])} (포함){branding_html}<br>"
        f"<strong>포함 릴리스:</strong> {summary['release_count']}개 · <strong>승인 항목:</strong> {len(report['items'])}개<br>"
        f"{escape(support_line('AS-IS', summary['from_support']))}<br>{escape(support_line('TO-BE', summary['to_support']))}</p>"
        f"<h2>적용 전 확인사항</h2><ul>{limitations_html}</ul>{items_html}</body></html>"
    )
