from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from releases.comparison import build_comparison_summary
from releases.forms import ComparisonForm, ReviewActionForm
from releases.models import ChangeItem, Release, Review, ReviewEvent, SourceSnapshot


@login_required
def comparison_view(request):
    area_choices = list(
        ChangeItem.objects.order_by("section__title").values_list("section__title", flat=True).distinct()
    )
    form = ComparisonForm(request.GET or None, area_choices=area_choices)
    summary = None
    page_obj = None
    selected_area = request.GET.get("area", "")
    selected_type = request.GET.get("change_type", "")
    view_mode = request.GET.get("view_mode", "review") or "review"

    if form.is_bound and form.is_valid():
        from_version = form.cleaned_data["from_version"]
        to_version = form.cleaned_data["to_version"]
        try:
            summary = build_comparison_summary(from_version, to_version)
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            release_ids = Release.objects.filter(version__in=summary["included_releases"]).values_list("id", flat=True)
            snapshot_ids = SourceSnapshot.objects.filter(is_current=True, release_id__in=release_ids).values_list("id", flat=True)
            items = ChangeItem.objects.filter(snapshot_id__in=snapshot_ids).select_related(
                "snapshot__release",
                "section",
                "review",
            )
            range_area_choices = list(
                items.order_by("section__title").values_list("section__title", flat=True).distinct()
            )
            form = ComparisonForm(request.GET, area_choices=range_area_choices)
            form.is_valid()
            if selected_type:
                items = items.filter(change_type=selected_type)
            if selected_area:
                items = items.filter(section__title=selected_area)
            if view_mode in ("customer", "dba"):
                items = items.filter(review__status=Review.Status.APPROVED)
            items = items.order_by("snapshot__release__release_date", "snapshot__release_id", "position")
            page_obj = Paginator(items, 50).get_page(request.GET.get("page"))
            for item in page_obj.object_list:
                review = getattr(item, "review", None)
                item.review_status = review.status if review else Review.Status.PENDING
                item.review_status_label = review.get_status_display() if review else Review.Status.PENDING.label
                item.display_text = review.edited_text if review and review.edited_text else item.text

    return render(
        request,
        "releases/comparison.html",
        {
            "form": form,
            "summary": summary,
            "page_obj": page_obj,
            "selected_area": selected_area,
            "selected_type": selected_type,
            "view_mode": view_mode,
        },
    )


@login_required
@require_POST
def review_change_item(request, item_id):
    if not request.user.is_staff:
        raise PermissionDenied("Staff role required")

    item = get_object_or_404(ChangeItem, pk=item_id)
    form = ReviewActionForm(request.POST)
    if not form.is_valid():
        raise PermissionDenied("Invalid review action")

    with transaction.atomic():
        review, _ = Review.objects.select_for_update().get_or_create(change_item=item)
        previous_status = review.status
        review.status = form.cleaned_data["action"]
        review.edited_text = form.cleaned_data["edited_text"].strip()
        review.note = form.cleaned_data["note"].strip()
        review.reviewer = request.user
        review.reviewed_at = timezone.now()
        review.save()
        ReviewEvent.objects.create(
            review=review,
            actor=request.user,
            previous_status=previous_status,
            new_status=review.status,
            edited_text=review.edited_text,
            note=review.note,
        )
        AuditLog.objects.create(
            actor=request.user,
            action=f"review.{review.status}",
            target_type="change_item",
            target_id=str(item.pk),
            detail={"previous_status": previous_status, "new_status": review.status},
        )

    next_url = request.POST.get("next", "")
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = reverse("releases:comparison")
    return redirect(next_url)
