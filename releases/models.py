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
