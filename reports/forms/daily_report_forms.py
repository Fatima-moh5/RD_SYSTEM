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
)


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
            "worker",
            "worker_name",
            "worker_source",
            "company_name",
            "skill_level",
            "normal_hours",
            "overtime_hours",
            "notes",
        ]

        widgets = {
            "master_code": forms.Select(attrs={"class": "form-select"}),
            "worker": forms.Select(attrs={"class": "form-select"}),

            "worker_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "worker_source": forms.Select(
                attrs={"class": "form-select"}
            ),

            "company_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "skill_level": forms.Select(
                attrs={"class": "form-select"}
            ),

            "normal_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),

            "overtime_hours": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 1,
                }
            ),
        }

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