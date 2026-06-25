from django import forms
from django.forms import inlineformset_factory

from reports.master_data.models import Project, ProjectArea
from reports.models import (
    DailyReport,
    WorkProgress,
    BlockedIssue,
    SiteVisit,
    WorkforceEntry,
    EquipmentUsage,
    MaterialReceipt,
    LookupItem,
    WorkerProfile,
)
def lookup_choices(list_type):
    return [("", "---------")] + [
        (item.value, item.value)
        for item in LookupItem.objects.filter(
            list_type=list_type,
            is_active=True
        ).order_by("sort_order", "value")
    ]

class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = [
            "project",
            "reference_date",
            "status",
            "weather_condition",
            "temperature",
            "weather_source",
            "weather_confirmed",
            "weather_note",
            "general_notes",
        ]
        widgets = {
            "reference_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "project": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "weather_condition": forms.TextInput(attrs={"class": "form-control"}),
            "temperature": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "weather_source": forms.Select(attrs={"class": "form-select"}),
            "weather_confirmed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "weather_note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "general_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, assigned_projects=None, **kwargs):
        super().__init__(*args, **kwargs)

        if assigned_projects is not None:
            self.fields["project"].queryset = assigned_projects
        else:
            self.fields["project"].queryset = Project.objects.filter(is_active=True)

        self.fields["project"].empty_label = "Select project"


class WorkProgressForm(forms.ModelForm):
    class Meta:
        model = WorkProgress
        fields = ["master_code", "description", "project_area", "quantity", "unit", "notes"]
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 1, "readonly": "readonly"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control compact-number", "step": "0.01"}),
            "unit": forms.TextInput(attrs={"class": "form-control compact-unit"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["project_area"].label = "Floor"
        self.fields["project_area"].queryset = ProjectArea.objects.none()

        if project:
            self.fields["project_area"].queryset = ProjectArea.objects.filter(
                project=project,
                is_active=True,
            )

        self.fields["project_area"].empty_label = "Select floor"


class BlockedIssueForm(forms.ModelForm):
    class Meta:
        model = BlockedIssue
        fields = ["master_code", "issue", "reason", "suggested_solution"]
        widgets = {
            "issue": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
            "suggested_solution": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
        }


class SiteVisitForm(forms.ModelForm):
    class Meta:
        model = SiteVisit
        fields = ["visit_code", "visitor_name", "visitor_entity", "purpose", "visit_time", "notes"]
        widgets = {
            "visit_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "purpose": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 1}),
        }


WorkProgressFormSet = inlineformset_factory(
    DailyReport,
    WorkProgress,
    form=WorkProgressForm,
    fk_name="daily_report",
    extra=1,
    can_delete=False,
)

BlockedIssueFormSet = inlineformset_factory(
    DailyReport,
    BlockedIssue,
    form=BlockedIssueForm,
    fk_name="daily_report",
    extra=1,
    can_delete=False,
)

SiteVisitFormSet = inlineformset_factory(
    DailyReport,
    SiteVisit,
    form=SiteVisitForm,
    fk_name="daily_report",
    extra=1,
    can_delete=False,
)

class WorkforceEntryForm(forms.ModelForm):
    class Meta:
        model = WorkforceEntry

        fields = [
            "master_code",
            "entry_type",
            "worker",
            "worker_name",
            "login_time",
            "logout_time",
            "sent_to_other_project",
            "external_source_type",
            "external_source_name",
            "trade_work_type",
            "number_of_workers",
            "skill_level",
            "notes",
        ]

        widgets = {
            "master_code": forms.Select(attrs={"class": "form-select"}),
            "entry_type": forms.Select(attrs={"class": "form-select workforce-entry-type"}),

            "worker": forms.Select(attrs={"class": "form-select workforce-rd-field"}),

            "worker_name": forms.TextInput(attrs={
                "class": "form-control workforce-rental-field",
                "placeholder": "Rental worker name",
            }),

            "login_time": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control workforce-time-field",
            }),

            "logout_time": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control workforce-time-field",
            }),

            "sent_to_other_project": forms.CheckboxInput(attrs={
                "class": "form-check-input workforce-rd-field",
            }),

            "external_source_type": forms.Select(attrs={
                "class": "form-select workforce-external-type",
            }),

            "external_source_name": forms.TextInput(attrs={
                "class": "form-control workforce-external-name",
                "placeholder": "Rental company or subcontractor name",
            }),

            "trade_work_type": forms.TextInput(attrs={
                "class": "form-control workforce-subcontractor-field",
                "placeholder": "Example: Plaster, Painting, Block work",
            }),

            "number_of_workers": forms.NumberInput(attrs={
                "class": "form-control workforce-subcontractor-field",
                "min": "1",
            }),

            "skill_level": forms.Select(attrs={"class": "form-select"}),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 1,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["worker"].queryset = WorkerProfile.objects.filter(
            worker_source="RD",
            is_active=True
        ).order_by("name")

        self.fields["worker"].empty_label = "Select RD worker"

        self.fields["skill_level"].choices = lookup_choices("skill_level")
        self.fields["external_source_type"].choices = lookup_choices("workforce")

    def clean(self):
        # Model-level WorkforceEntry.clean() already contains the final validation rules.
        # Keeping validation in one place prevents duplicate error messages in the UI.
        return super().clean()

WorkforceEntryFormSet = inlineformset_factory(
    DailyReport,
    WorkforceEntry,
    form=WorkforceEntryForm,
    fk_name="daily_report",
    extra=1,
    can_delete=False,
)

EquipmentUsageFormSet = inlineformset_factory(
    DailyReport,
    EquipmentUsage,
    fk_name="daily_report",
    fields=["master_code", "equipment", "quantity", "working_hours", "idle_hours", "notes"],
    extra=1,
    can_delete=False,
)

MaterialReceiptFormSet = inlineformset_factory(
    DailyReport,
    MaterialReceipt,
    fk_name="daily_report",
    fields=["master_code", "material_name", "quantity", "unit", "supplier", "delivery_note_number", "notes"],
    extra=1,
    can_delete=False,
)