import re
from collections import Counter
from dataclasses import dataclass

from releases.models import ChangeItem, Release, ReleaseSection, SourceSnapshot, VersionSupport


VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:(beta|rc)(\d+))?$")
STAGE_ORDER = {"beta": 0, "rc": 1, None: 2}


@dataclass(frozen=True, order=True)
class PostgreSQLVersion:
    sort_key: tuple[int, int, int, int]
    value: str

    @classmethod
    def parse(cls, value):
        match = VERSION_PATTERN.fullmatch(value.lower())
        if not match:
            raise ValueError(f"Unsupported PostgreSQL version: {value}")

        first = int(match.group(1))
        second = int(match.group(2) or 0)
        third = int(match.group(3) or 0)
        stage = match.group(4)
        prerelease_number = int(match.group(5) or 0)

        if first < 10:
            family_minor = second
            patch = prerelease_number if stage else third
        else:
            family_minor = 0
            patch = prerelease_number if stage else second

        return cls(sort_key=(first, family_minor, STAGE_ORDER[stage], patch), value=value)

    @property
    def family(self):
        first, family_minor, _, _ = self.sort_key
        return f"{first}.{family_minor}" if first < 10 else str(first)

    @property
    def is_prerelease(self):
        return self.sort_key[2] < STAGE_ORDER[None]


def versions_in_upgrade_range(available_versions, from_version, to_version, include_prereleases=False):
    parsed_from = PostgreSQLVersion.parse(from_version)
    parsed_to = PostgreSQLVersion.parse(to_version)
    if parsed_from >= parsed_to:
        raise ValueError("TO-BE version must be newer than AS-IS version")
    if not include_prereleases and (parsed_from.is_prerelease or parsed_to.is_prerelease):
        raise ValueError("Beta/RC endpoints require include_prereleases")

    parsed_available = sorted(PostgreSQLVersion.parse(version) for version in available_versions)
    available_values = {version.value for version in parsed_available}
    missing = [version for version in (from_version, to_version) if version not in available_values]
    if missing:
        raise ValueError(f"Release data not found: {', '.join(missing)}")

    return [
        version.value
        for version in parsed_available
        if parsed_from < version <= parsed_to and (include_prereleases or not version.is_prerelease)
    ]


def build_comparison_summary(from_version, to_version, include_prereleases=False):
    releases = list(Release.objects.all())
    release_by_version = {release.version: release for release in releases}
    selected_versions = versions_in_upgrade_range(
        release_by_version,
        from_version,
        to_version,
        include_prereleases=include_prereleases,
    )
    selected_releases = [release_by_version[version] for version in selected_versions]
    current_snapshots = SourceSnapshot.objects.filter(
        is_current=True,
        release_id__in=[release.id for release in selected_releases],
    )

    major_releases = [release.version for release in selected_releases if release.kind == Release.Kind.MAJOR]
    minor_releases = [release.version for release in selected_releases if release.kind == Release.Kind.MINOR]
    prereleases = [
        release.version
        for release in selected_releases
        if release.kind in (Release.Kind.BETA, Release.Kind.RC)
    ]
    change_type_counts = Counter(
        ChangeItem.objects.filter(snapshot__in=current_snapshots).values_list("change_type", flat=True)
    )
    support_by_series = {support.series: support for support in VersionSupport.objects.all()}

    def support_summary(version):
        parsed_version = PostgreSQLVersion.parse(version)
        support = support_by_series.get(parsed_version.family)
        if support is None:
            return None
        return {
            "series": support.series,
            "current_minor": support.current_minor,
            "supported": support.supported,
            "first_release_date": support.first_release_date.isoformat(),
            "final_release_date": support.final_release_date.isoformat(),
        }

    return {
        "from_version": from_version,
        "to_version": to_version,
        "included_rule": "greater_than_from_and_less_than_or_equal_to_to",
        "include_prereleases": include_prereleases,
        "release_count": len(selected_releases),
        "major_release_count": len(major_releases),
        "minor_release_count": len(minor_releases),
        "prerelease_count": len(prereleases),
        "section_count": ReleaseSection.objects.filter(snapshot__in=current_snapshots).count(),
        "change_item_count": ChangeItem.objects.filter(snapshot__in=current_snapshots).count(),
        "change_type_counts": dict(sorted(change_type_counts.items())),
        "major_releases": major_releases,
        "minor_releases": minor_releases,
        "prereleases": prereleases,
        "included_releases": selected_versions,
        "from_support": support_summary(from_version),
        "to_support": support_summary(to_version),
    }
