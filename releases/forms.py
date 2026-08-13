from django import forms

from releases.comparison import PostgreSQLVersion
from releases.models import ChangeItem, Release


class ComparisonForm(forms.Form):
    from_version = forms.ChoiceField(label="AS-IS")
    to_version = forms.ChoiceField(label="TO-BE")
    change_type = forms.ChoiceField(label="변경 유형", required=False)
    area = forms.ChoiceField(label="분야", required=False)
    view_mode = forms.ChoiceField(
        label="보기 수준",
        required=False,
        choices=(("review", "내부 검토"), ("customer", "고객용 승인본"), ("dba", "DBA용 승인본")),
    )

    def __init__(self, *args, area_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        versions = sorted(
            (PostgreSQLVersion.parse(version) for version in Release.objects.values_list("version", flat=True)),
            reverse=True,
        )
        version_choices = [(version.value, version.value) for version in versions if not version.is_prerelease]
        self.fields["from_version"].choices = version_choices
        self.fields["to_version"].choices = version_choices
        self.fields["change_type"].choices = [("", "전체 유형"), *ChangeItem.ChangeType.choices]
        self.fields["area"].choices = [("", "전체 분야"), *((area, area) for area in area_choices)]

        for field in self.fields.values():
            field.widget.attrs["class"] = "field-control"


class ReviewActionForm(forms.Form):
    action = forms.ChoiceField(choices=(("approved", "승인"), ("rejected", "반려"), ("pending", "검토 대기")))
    edited_text = forms.CharField(required=False, widget=forms.Textarea)
    note = forms.CharField(required=False, widget=forms.Textarea)
