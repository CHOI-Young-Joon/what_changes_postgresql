from django.contrib import admin

from .models import JobRun, Release, SourceSnapshot


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
