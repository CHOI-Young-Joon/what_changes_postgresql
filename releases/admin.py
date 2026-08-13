from django.contrib import admin

from .models import (
    ChangeItem,
    JobRun,
    Release,
    ReleaseSection,
    SourceSnapshot,
    VersionSupport,
    VersionSupportSnapshot,
    Review,
    ReviewEvent,
    ReportProfile,
)


@admin.register(ReportProfile)
class ReportProfileAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "project_name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("customer_name", "project_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("version", "kind", "release_date", "updated_at")
    list_filter = ("kind",)
    search_fields = ("version", "source_url")
    readonly_fields = ("discovered_at", "updated_at")


@admin.register(SourceSnapshot)
class SourceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("release", "content_sha256_short", "fetched_at", "is_current")
    list_filter = ("is_current", "content_type")
    search_fields = ("release__version", "content_sha256", "source_url")
    readonly_fields = (
        "release",
        "source_url",
        "http_status",
        "content_type",
        "etag",
        "last_modified",
        "content_sha256",
        "raw_html",
        "extracted_text",
        "storage_path",
        "fetched_at",
        "is_current",
        "parser_version",
        "parsed_at",
        "parse_error",
    )

    @admin.display(description="SHA-256")
    def content_sha256_short(self, obj):
        return obj.content_sha256[:12]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReleaseSection)
class ReleaseSectionAdmin(admin.ModelAdmin):
    list_display = ("release_version", "position", "level", "title", "source_id")
    list_filter = ("level",)
    search_fields = ("snapshot__release__version", "title", "source_id", "body_text")
    readonly_fields = ("snapshot", "parent", "source_id", "title", "level", "position", "body_text")

    @admin.display(description="Release")
    def release_version(self, obj):
        return obj.snapshot.release.version

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChangeItem)
class ChangeItemAdmin(admin.ModelAdmin):
    list_display = ("release_version", "position", "change_type", "section", "text_preview")
    list_filter = ("change_type", "classification_version")
    search_fields = ("snapshot__release__version", "section__title", "text", "item_sha256")
    readonly_fields = (
        "snapshot",
        "section",
        "position",
        "item_sha256",
        "text",
        "raw_html",
        "change_type",
        "classification_rule",
        "classification_version",
    )

    @admin.display(description="Release")
    def release_version(self, obj):
        return obj.snapshot.release.version

    @admin.display(description="Text")
    def text_preview(self, obj):
        return obj.text[:120]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VersionSupport)
class VersionSupportAdmin(admin.ModelAdmin):
    list_display = ("series", "current_minor", "supported", "first_release_date", "final_release_date", "updated_at")
    list_filter = ("supported",)
    search_fields = ("series", "current_minor")
    readonly_fields = ("series", "current_minor", "supported", "first_release_date", "final_release_date", "snapshot", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VersionSupportSnapshot)
class VersionSupportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("fetched_at", "content_sha256_short", "is_current")
    list_filter = ("is_current",)
    readonly_fields = ("source_url", "content_sha256", "raw_html", "storage_path", "fetched_at", "is_current")

    @admin.display(description="SHA-256")
    def content_sha256_short(self, obj):
        return obj.content_sha256[:12]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("change_item", "status", "reviewer", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("change_item__text", "edited_text", "note", "reviewer__username")
    readonly_fields = ("change_item", "status", "edited_text", "note", "reviewer", "reviewed_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReviewEvent)
class ReviewEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "review", "previous_status", "new_status", "actor")
    list_filter = ("previous_status", "new_status")
    readonly_fields = ("review", "actor", "previous_status", "new_status", "edited_text", "note", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("started_at", "job_type", "status", "created_count", "unchanged_count", "failed_count")
    list_filter = ("job_type", "status")
    readonly_fields = (
        "job_type",
        "status",
        "started_at",
        "finished_at",
        "discovered_count",
        "created_count",
        "unchanged_count",
        "failed_count",
        "errors",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
