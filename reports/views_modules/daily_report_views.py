from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reports.forms.daily_report_forms import (
    DailyReportForm,
    WorkProgressFormSet,
    BlockedIssueFormSet,
    SiteVisitFormSet,
    WorkforceEntryFormSet,
    EquipmentUsageFormSet,
    MaterialReceiptFormSet,
)

from reports.master_data.models import (
    Project,
    ProjectAssignment,
    ProjectPhase,
    Category,
    Subcategory,
    MasterCode,
)

from reports.models import (
    DailyReport,
    DailyReportChangeLog,
    DailyReportAttachment,
)

from reports.services.weather_service import fetch_weather


DAILY_REPORT_FORM_TEMPLATE = "reports/forms/daily_report/daily_report_form.html"
DAILY_REPORT_LIST_TEMPLATE = "reports/forms/daily_report/daily_report_list.html"
DAILY_REPORT_PRINT_TEMPLATE = "reports/forms/daily_report/daily_report_print.html"


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def can_view_all_reports(user):
    return (
        user.is_superuser
        or user_in_group(user, "Admin")
        or user_in_group(user, "Project Manager")
        or user_in_group(user, "Department Manager")
        or user_in_group(user, "Operation")
        or user_in_group(user, "Cost Control")
    )


def get_assigned_projects(user, role=None):
    assignments = ProjectAssignment.objects.filter(
        user=user,
        is_active=True,
        project__is_active=True,
    ).select_related("project")

    if role:
        assignments = assignments.filter(role=role)

    projects = Project.objects.filter(
        id__in=assignments.values_list("project_id", flat=True)
    ).distinct()

    if projects.exists():
        return projects

    return Project.objects.filter(
        site_engineer__iexact=user.username,
        is_active=True,
    )


def get_reports_for_user(user):
    if can_view_all_reports(user):
        return DailyReport.objects.select_related("project", "created_by").all()

    assigned_projects = get_assigned_projects(user)

    return DailyReport.objects.select_related("project", "created_by").filter(
        project__in=assigned_projects
    )


def check_report_permission(user, report):
    if can_view_all_reports(user):
        return True

    if report.created_by_id == user.id:
        return True

    assigned_projects = get_assigned_projects(user)

    if report.project in assigned_projects:
        return True

    raise PermissionDenied("You do not have permission to access this report.")


def get_week_range(today):
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_formsets(data=None, report=None, project=None):
    return {
        "work_progress_formset": WorkProgressFormSet(
            data=data,
            instance=report,
            prefix="work",
            form_kwargs={"project": project},
        ),
        "blocked_issue_formset": BlockedIssueFormSet(
            data=data,
            instance=report,
            prefix="blocked",
        ),
        "site_visit_formset": SiteVisitFormSet(
            data=data,
            instance=report,
            prefix="visits",
        ),
        "workforce_formset": WorkforceEntryFormSet(
            data=data,
            instance=report,
            prefix="workforce",
        ),
        "equipment_formset": EquipmentUsageFormSet(
            data=data,
            instance=report,
            prefix="equipment",
        ),
        "material_formset": MaterialReceiptFormSet(
            data=data,
            instance=report,
            prefix="materials",
        ),
    }


def formsets_are_valid(formsets):
    return all(formset.is_valid() for formset in formsets.values())


def save_formsets(formsets):
    for formset in formsets.values():
        formset.save()


def save_attachments(report, files):
    for uploaded_file in files.getlist("attachments"):
        DailyReportAttachment.objects.create(
            report=report,
            file=uploaded_file,
        )


def apply_weather_to_report(report, project):
    if not project or not project.latitude or not project.longitude:
        return False

    weather_data = fetch_weather(project.latitude, project.longitude)

    report.weather_condition = weather_data.get("weather_condition", "")
    report.temperature = weather_data.get("temperature")
    report.weather_source = DailyReport.WEATHER_SOURCE_API_CONFIRMED
    report.weather_confirmed = True

    return True


def log_report_changes(report, old_values, new_values, user):
    changed_fields = []

    for field_name, old_value in old_values.items():
        new_value = new_values.get(field_name)

        old_text = "" if old_value is None else str(old_value)
        new_text = "" if new_value is None else str(new_value)

        if old_text != new_text:
            DailyReportChangeLog.objects.create(
                report=report,
                edited_by=user,
                field_name=field_name,
                old_value=old_text,
                new_value=new_text,
            )
            changed_fields.append(field_name)

    return changed_fields


def get_master_code_context():
    return {
        "project_phases": ProjectPhase.objects.filter(
            is_active=True
        ).order_by("display_order"),

        "categories": Category.objects.filter(
            is_active=True
        ).order_by("symbol"),

        "subcategories": Subcategory.objects.filter(
            is_active=True
        ).select_related(
            "category"
        ).order_by(
            "category__symbol",
            "symbol",
        ),

        "master_codes": MasterCode.objects.filter(
            is_active=True,
        ).select_related(
            "project_phase",
            "category",
            "subcategory",
        ).order_by(
            "project_phase__display_order",
            "category__symbol",
            "subcategory__symbol",
        ),
    }


@login_required
def daily_report_list(request):
    reports = get_reports_for_user(request.user)

    filter_type = request.GET.get("filter", "")
    project_id = request.GET.get("project", "")
    status = request.GET.get("status", "")

    today = timezone.localdate()

    if filter_type == "week":
        week_start, week_end = get_week_range(today)
        reports = reports.filter(reference_date__range=[week_start, week_end])

    elif filter_type == "month":
        reports = reports.filter(
            reference_date__year=today.year,
            reference_date__month=today.month,
        )

    if project_id:
        reports = reports.filter(project_id=project_id)

    if status:
        reports = reports.filter(status=status)

    projects = (
        get_reports_for_user(request.user)
        .exclude(project__isnull=True)
        .values("project_id", "project__name")
        .distinct()
        .order_by("project__name")
    )

    context = {
        "page_title": "Daily Reports",
        "reports": reports,
        "projects": projects,
        "filter_type": filter_type,
        "selected_project": project_id,
        "selected_status": status,
        "can_view_all": can_view_all_reports(request.user),
    }

    return render(request, DAILY_REPORT_LIST_TEMPLATE, context)


@login_required
@transaction.atomic
def daily_report_create(request):
    assigned_projects = get_assigned_projects(
        request.user,
        role=ProjectAssignment.ROLE_SITE_ENGINEER,
    )

    if not assigned_projects.exists():
        messages.error(
            request,
            f"No active site project is assigned to your username: {request.user.username}."
        )
        return redirect("daily_report_list")

    default_project = assigned_projects.first()

    report = DailyReport(
        created_by=request.user,
        project=default_project,
        reference_date=timezone.localdate(),
    )

    weather_warning = None

    try:
        weather_loaded = apply_weather_to_report(report, default_project)
        if not weather_loaded:
            weather_warning = "Project latitude/longitude is missing. Weather was not loaded."
    except Exception as e:
        weather_warning = f"Weather API failed: {str(e)}"

    if request.method == "POST":
        form = DailyReportForm(
            request.POST,
            assigned_projects=assigned_projects,
        )

        selected_project = default_project

        if form.is_valid():
            selected_project = form.cleaned_data.get("project") or default_project

        formsets = build_formsets(
            data=request.POST,
            report=report,
            project=selected_project,
        )

        if form.is_valid() and formsets_are_valid(formsets):
            report = form.save(commit=False)
            report.created_by = request.user

            if not report.project:
                report.project = default_project

            try:
                apply_weather_to_report(report, report.project)
            except Exception:
                pass

            report.save()

            formsets = build_formsets(
                data=request.POST,
                report=report,
                project=report.project,
            )

            if formsets_are_valid(formsets):
                save_formsets(formsets)
                save_attachments(report, request.FILES)

            messages.success(request, "Daily report created successfully.")
            return redirect("daily_report_edit", pk=report.pk)

        messages.error(request, "Please correct the errors before saving.")

    else:
        initial_data = {
            "project": default_project,
            "reference_date": timezone.localdate(),
            "weather_condition": report.weather_condition,
            "temperature": report.temperature,
            "weather_source": report.weather_source,
            "weather_confirmed": report.weather_confirmed,
        }

        form = DailyReportForm(
            initial=initial_data,
            assigned_projects=assigned_projects,
        )

        formsets = build_formsets(report=report, project=default_project)

        if weather_warning:
            messages.warning(request, weather_warning)

    context = {
        "page_title": "Daily Report",
        "form": form,
        "report": None,
        "assigned_projects": assigned_projects,
        "assigned_project": default_project,
        "mode": "create",
        "changed_fields": [],
        **get_master_code_context(),
        **formsets,
    }

    return render(request, DAILY_REPORT_FORM_TEMPLATE, context)


@login_required
@transaction.atomic
def daily_report_edit(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    assigned_projects = get_assigned_projects(request.user)

    tracked_fields = [
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

    old_values = {field: getattr(report, field) for field in tracked_fields}

    if request.method == "POST":
        form = DailyReportForm(
            request.POST,
            instance=report,
            assigned_projects=assigned_projects if not can_view_all_reports(request.user) else None,
        )

        selected_project = report.project

        if form.is_valid():
            selected_project = form.cleaned_data.get("project") or report.project

        formsets = build_formsets(
            data=request.POST,
            report=report,
            project=selected_project,
        )

        if form.is_valid() and formsets_are_valid(formsets):
            report = form.save()
            save_formsets(formsets)
            save_attachments(report, request.FILES)

            new_values = {field: getattr(report, field) for field in tracked_fields}

            changed_fields = log_report_changes(
                report=report,
                old_values=old_values,
                new_values=new_values,
                user=request.user,
            )

            request.session["changed_fields"] = changed_fields

            if changed_fields:
                messages.success(request, "Report updated. Edited fields are highlighted.")
            else:
                messages.success(request, "Report saved. No main report fields were changed.")

            return redirect("daily_report_edit", pk=report.pk)

        messages.error(request, "Please correct the errors before saving.")

    else:
        form = DailyReportForm(
            instance=report,
            assigned_projects=assigned_projects if not can_view_all_reports(request.user) else None,
        )

        formsets = build_formsets(report=report, project=report.project)

    changed_fields = request.session.pop("changed_fields", [])

    context = {
        "page_title": "Daily Report",
        "form": form,
        "report": report,
        "mode": "edit",
        "changed_fields": changed_fields,
        "change_logs": report.change_logs.all()[:20],
        **get_master_code_context(),
        **formsets,
    }

    return render(request, DAILY_REPORT_FORM_TEMPLATE, context)


@login_required
def daily_report_print(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    return render(
        request,
        DAILY_REPORT_PRINT_TEMPLATE,
        {
            "page_title": "Print Daily Report",
            "report": report,
        },
    )