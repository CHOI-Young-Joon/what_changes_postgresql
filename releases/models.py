from django.db import models


class Release(models.Model):
    class Kind(models.TextChoices):
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor"
        BETA = "beta", "Beta"
        RC = "rc", "Release candidate"

    version = models.CharField(max_length=32, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    release_date = models.DateField(null=True, blank=True)
    source_url = models.URLField(max_length=500)
    discovered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-release_date", "-id"]

    def __str__(self):
        return f"PostgreSQL {self.version}"


class SourceSnapshot(models.Model):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="snapshots")
    source_url = models.URLField(max_length=500)
    http_status = models.PositiveSmallIntegerField(default=200)
    content_type = models.CharField(max_length=200, blank=True)
    etag = models.CharField(max_length=500, blank=True)
    last_modified = models.CharField(max_length=200, blank=True)
    content_sha256 = models.CharField(max_length=64)
    raw_html = models.TextField()
    extracted_text = models.TextField()
    storage_path = models.CharField(max_length=500)
    fetched_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)
    parser_version = models.CharField(max_length=32, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    parse_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-fetched_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["release", "content_sha256"],
                name="unique_release_snapshot_content",
            )
        ]

    def __str__(self):
        return f"{self.release.version} / {self.content_sha256[:12]}"


class ReleaseSection(models.Model):
    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.CASCADE, related_name="sections")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    source_id = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=500)
    level = models.PositiveSmallIntegerField()
    position = models.PositiveIntegerField()
    body_text = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "position"], name="unique_snapshot_section_position")
        ]

    def __str__(self):
        return f"{self.snapshot.release.version} / {self.title}"


class ChangeItem(models.Model):
    class ChangeType(models.TextChoices):
        ADDED = "added", "Added"
        CHANGED = "changed", "Changed"
        DEPRECATED = "deprecated", "Deprecated"
        REMOVED = "removed", "Removed"
        FIXED = "fixed", "Fixed"
        SECURITY = "security", "Security"
        OTHER = "other", "Other"

    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.CASCADE, related_name="change_items")
    section = models.ForeignKey(ReleaseSection, on_delete=models.CASCADE, related_name="change_items")
    position = models.PositiveIntegerField()
    item_sha256 = models.CharField(max_length=64)
    text = models.TextField()
    raw_html = models.TextField()
    change_type = models.CharField(max_length=16, choices=ChangeType.choices, default=ChangeType.OTHER)
    classification_rule = models.CharField(max_length=100, blank=True)
    classification_version = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "position"], name="unique_snapshot_change_position")
        ]

    def __str__(self):
        return f"{self.snapshot.release.version} / item {self.position}"


class VersionSupportSnapshot(models.Model):
    source_url = models.URLField(max_length=500)
    content_sha256 = models.CharField(max_length=64, unique=True)
    raw_html = models.TextField()
    storage_path = models.CharField(max_length=500)
    fetched_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self):
        return f"Version support / {self.content_sha256[:12]}"


class VersionSupport(models.Model):
    series = models.CharField(max_length=16, unique=True)
    current_minor = models.CharField(max_length=32)
    supported = models.BooleanField()
    first_release_date = models.DateField()
    final_release_date = models.DateField()
    snapshot = models.ForeignKey(VersionSupportSnapshot, on_delete=models.PROTECT, related_name="support_rows")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-first_release_date"]

    def __str__(self):
        return f"PostgreSQL {self.series} ({'supported' if self.supported else 'unsupported'})"


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "검토 대기"
        APPROVED = "approved", "승인"
        REJECTED = "rejected", "반려"

    change_item = models.OneToOneField(ChangeItem, on_delete=models.CASCADE, related_name="review")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    edited_text = models.TextField(blank=True)
    note = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="release_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.change_item} / {self.status}"


class ReviewEvent(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="review_events")
    previous_status = models.CharField(max_length=16, choices=Review.Status.choices)
    new_status = models.CharField(max_length=16, choices=Review.Status.choices)
    edited_text = models.TextField(blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class JobRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    job_type = models.CharField(max_length=100)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    discovered_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    unchanged_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.job_type} / {self.status} / {self.started_at:%Y-%m-%d %H:%M:%S}"
