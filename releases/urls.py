from django.urls import path

from releases.views import comparison_view, export_report, review_change_item


app_name = "releases"

urlpatterns = [
    path("", comparison_view, name="comparison"),
    path("reviews/<int:item_id>/", review_change_item, name="review-item"),
    path("reports/export/", export_report, name="export-report"),
]
