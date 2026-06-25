from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
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
    ProjectArea,
    ProjectPhase,
    Category,
    Subcategory,
    MasterCode,
)

from reports.models import (
    DailyReport,
    DailyReportChangeLog,
    DailyReportAttachment,
    BlockedIssue,
    WorkProgress,
)

from reports.services.weather_service import fetch_weather


DAILY_REPORT_FORM_TEMPLATE = "reports/forms/daily_report/daily_report_form.html"
DAILY_REPORT_LIST_TEMPLATE = "reports/forms/daily_report/daily_report_list.html"
DAILY_REPORT_REVIEW_TEMPLATE = "reports/forms/daily_report/daily_report_review.html"
DAILY_REPORT_PRINT_TEMPLATE = "reports/forms/daily_report/daily_report_print.html"


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def can_view_all_reports(user):
    return (
        user.is_superuser
        or user_in_group(user, "Admin")
        or user_in_group(user, "Project_mgr")
        or user_in_group(user, "dep_mgr")
        or user_in_group(user, "operations")
        or user_in_group(user, "Cost_Control")
    )


def is_project_manager(user):
    return user_in_group(user, "Project_mgr")


def is_department_manager(user):
    return user_in_group(user, "dep_mgr")


def is_site_engineer(user):
    return user_in_group(user, "site_eng")


def is_admin_user(user):
    return user.is_superuser or user_in_group(user, "Admin")


def can_pm_review_report(user, report):
    """
    Zero-tolerance PM decision permission.
    Only Admin/superuser, assigned Project Manager, or Department Manager can
    approve, return, or reject a daily report.
    """
    if is_admin_user(user):
        return True

    if is_department_manager(user):
        return True

    if is_project_manager(user):
        pm_projects = get_assigned_projects(
            user,
            role=ProjectAssignment.ROLE_PROJECT_MANAGER,
        )
        return pm_projects.filter(pk=report.project_id).exists()

    return False


def can_view_blocked_issues(user):
    return (
        is_admin_user(user)
        or is_site_engineer(user)
        or is_project_manager(user)
        or is_department_manager(user)
    )


def can_manage_blocked_issues(user):
    return (
        is_admin_user(user)
        or is_project_manager(user)
        or is_department_manager(user)
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


def can_edit_report(user, report):
    if user.is_superuser:
        return True

    if is_project_manager(user) or is_department_manager(user):
        return False

    if report.created_by_id != user.id:
        return False

    return report.status in [
        DailyReport.STATUS_DRAFT,
        DailyReport.STATUS_RETURNED,
    ]


def get_related_items(report, model_name_keyword):
    for relation in report._meta.related_objects:
        model_name = relation.related_model.__name__.lower()
        accessor = relation.get_accessor_name()

        if model_name_keyword.lower() in model_name:
            manager = getattr(report, accessor, None)

            if manager is not None:
                try:
                    return manager.all()
                except Exception:
                    return []

    return []


def safe_set_attr(instance, field_name, value):
    field_names = {field.name for field in instance._meta.fields}

    if field_name in field_names:
        setattr(instance, field_name, value)
        return True

    return False


def get_week_range(today):
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def build_formsets(data=None, report=None, project=None):
    work_progress_kwargs = {
        "data": data,
        "instance": report,
        "prefix": "work",
        "form_kwargs": {"project": project},
    }

    # UX rule:
    # Existing Active Works are shown as history rows.
    # The formset shows only one new editable row.
    if report is not None and getattr(report, "pk", None):
        work_progress_kwargs["queryset"] = WorkProgress.objects.none()

    return {
        "work_progress_formset": WorkProgressFormSet(**work_progress_kwargs),

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


def formset_has_data(formset):
    """
    Returns True if the user entered real data in at least one row.
    Empty optional rows are ignored.
    """
    for form in formset.forms:
        if not form.has_changed():
            continue

        cleaned = getattr(form, "cleaned_data", None)
        if cleaned and cleaned.get("DELETE"):
            continue

        return True

    return False


def get_formset_friendly_name(key):
        names = {
            "work_progress_formset": "Active Works",
            "blocked_issue_formset": "Blocked Issues",
            "site_visit_formset": "Site Visits",
            "workforce_formset": "Workforce",
            "equipment_formset": "Equipment Usage",
            "material_formset": "Material Receipts",
        }
        return names.get(key, key)



def request_has_work_progress_data(data):
    """
    Checks the posted Active Works formset directly.
    This is intentionally independent from the visual one-row history UI.
    """
    if not data:
        return False

    try:
        total_forms = int(data.get("work-TOTAL_FORMS", 0) or 0)
    except (TypeError, ValueError):
        total_forms = 0

    work_fields = [
        "master_code",
        "description",
        "project_area",
        "quantity",
        "unit",
        "notes",
    ]

    for index in range(total_forms):
        for field_name in work_fields:
            value = data.get(f"work-{index}-{field_name}", "")
            if str(value).strip():
                return True

    return False


def report_has_saved_work_progress(report):
    return bool(
        report
        and getattr(report, "pk", None)
        and report.work_progress_items.exists()
    )


def validate_daily_report_for_action(form, formsets, action):
    """
    UAT rules:
    - Save Draft: main report must be valid; optional entered rows should be valid.
    - Submit: project/date/weather + at least one Active Work saved or posted.
    - Active Works are saved through a controlled custom saver to support the one-active-row UX.
    """
    errors = []

    if not form.is_valid():
        errors.append("Please complete the main report information before saving.")
        return False, errors

    for key, formset in formsets.items():
        # Active Works are handled separately because existing rows are displayed as history
        # and the formset is intentionally used only for the current new entry.
        if key == "work_progress_formset":
            continue

        if formset_has_data(formset) and not formset.is_valid():
            errors.append(
                f"{get_formset_friendly_name(key)} has incomplete information: "
                f"{formset.errors} {formset.non_form_errors()}"
            )

    if errors:
        return False, errors

    if action == "draft":
        return True, errors

    project = form.cleaned_data.get("project")
    reference_date = form.cleaned_data.get("reference_date")
    weather_condition = form.cleaned_data.get("weather_condition")
    temperature = form.cleaned_data.get("temperature")

    if not project:
        errors.append("Please select the project before submitting the daily report.")

    if not reference_date:
        errors.append("Please select the report date before submitting.")

    if not weather_condition and temperature in [None, ""]:
        errors.append(
            "Weather information is required before submitting. "
            "Please confirm the weather or fill it manually."
        )

    active_work_formset = formsets.get("work_progress_formset")
    active_work_report = active_work_formset.instance if active_work_formset else None

    has_existing_active_work = report_has_saved_work_progress(active_work_report)
    has_posted_active_work = request_has_work_progress_data(active_work_formset.data if active_work_formset else None)

    if not has_existing_active_work and not has_posted_active_work:
        errors.append("Please add at least one Active Work before submitting the daily report.")

    return len(errors) == 0, errors



def parse_decimal_or_none(value):
    value = str(value or "").strip()
    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def save_work_progress_entries(report, data):
    """
    Saves only newly posted Active Works.

    Existing Active Works are displayed as read-only history rows in the template.
    The editable form is one current entry only, so this function creates new
    WorkProgress rows instead of trying to edit historical rows.
    """
    if not report or not getattr(report, "pk", None) or not data:
        return

    try:
        total_forms = int(data.get("work-TOTAL_FORMS", 0) or 0)
    except (TypeError, ValueError):
        total_forms = 0

    for index in range(total_forms):
        master_code_id = str(data.get(f"work-{index}-master_code", "") or "").strip()
        description = str(data.get(f"work-{index}-description", "") or "").strip()
        project_area_id = str(data.get(f"work-{index}-project_area", "") or "").strip()
        quantity = parse_decimal_or_none(data.get(f"work-{index}-quantity"))
        unit = str(data.get(f"work-{index}-unit", "") or "").strip()
        notes = str(data.get(f"work-{index}-notes", "") or "").strip()

        if not any([master_code_id, description, project_area_id, quantity is not None, unit, notes]):
            continue

        master_code = None
        if master_code_id:
            master_code = MasterCode.objects.filter(pk=master_code_id).first()

        project_area = None
        if project_area_id:
            project_area = ProjectArea.objects.filter(
                pk=project_area_id,
                project=report.project,
                is_active=True,
            ).first()

        if master_code and not description:
            description = master_code.description or ""

        WorkProgress.objects.create(
            daily_report=report,
            master_code=master_code,
            description=description,
            project_area=project_area,
            quantity=quantity,
            unit=unit,
            notes=notes,
        )


def save_formsets(formsets):
    """
    Saves all non-Active-Works formsets.

    Active Works are saved separately by save_work_progress_entries() so the UI can
    keep exactly one current entry form and show existing entries as history rows.
    """
    for key, formset in formsets.items():
        if key == "work_progress_formset" or getattr(formset, "prefix", "") == "work":
            continue

        if formset.is_valid():
            formset.save()


def save_attachments(report, files):
    for uploaded_file in files.getlist("attachments"):
        DailyReportAttachment.objects.create(
            daily_report=report,
            file=uploaded_file,
            uploaded_by=getattr(report, "created_by", None),
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
        "can_pm_review": can_manage_blocked_issues(request.user),
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

        action = request.POST.get("action", "draft")

        is_ready, validation_errors = validate_daily_report_for_action(
            form=form,
            formsets=formsets,
            action=action,
        )

        if is_ready:
            report = form.save(commit=False)
            report.created_by = request.user

            if not report.project:
                report.project = default_project

            if action == "submit":
                report.status = DailyReport.STATUS_SUBMITTED
                report.submitted_at = timezone.now()
            else:
                report.status = DailyReport.STATUS_DRAFT

            try:
                apply_weather_to_report(report, report.project)
            except Exception:
                pass

            existing_report = DailyReport.objects.filter(
                project=report.project,
                reference_date=report.reference_date,
                created_by=request.user,
            ).first()

            if existing_report:
                messages.warning(
                    request,
                    "A Daily Report already exists for this project and date. "
                    "The existing report has been opened."
                )
                return redirect("daily_report_edit", pk=existing_report.pk)

            try:
                report.save()
            except IntegrityError:
                existing_report = DailyReport.objects.get(
                    project=report.project,
                    reference_date=report.reference_date,
                    created_by=request.user,
                )

                messages.warning(
                    request,
                    "A Daily Report already exists for this project and date. "
                    "The existing report has been opened."
                )
                return redirect("daily_report_edit", pk=existing_report.pk)

            formsets = build_formsets(
                data=request.POST,
                report=report,
                project=report.project,
            )

            save_work_progress_entries(report, request.POST)
            save_formsets(formsets)
            save_attachments(report, request.FILES)

            messages.success(request, "Daily report created successfully.")
            return redirect("daily_report_edit", pk=report.pk)

        for error in validation_errors:
            messages.error(request, error)

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
        "work_progress_history": [],
        **get_master_code_context(),
        **formsets,
    }

    return render(request, DAILY_REPORT_FORM_TEMPLATE, context)


@login_required
@transaction.atomic

def daily_report_edit(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if can_pm_review_report(request.user, report) and not is_admin_user(request.user):
        return redirect("daily_report_review", pk=report.pk)

    if request.method == "POST" and not can_edit_report(request.user, report):
        messages.error(request, "This report is locked and cannot be edited.")

        if can_pm_review_report(request.user, report):
            return redirect("daily_report_review", pk=report.pk)

        return redirect("daily_report_print", pk=report.pk)

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

        action = request.POST.get("action", "draft")
        is_ready, validation_errors = validate_daily_report_for_action(
            form=form,
            formsets=formsets,
            action=action,
        )

        if is_ready:
            report = form.save(commit=False)

            if action == "submit":
                report.status = DailyReport.STATUS_SUBMITTED
                report.submitted_at = timezone.now()
            else:
                report.status = DailyReport.STATUS_DRAFT

            report.save()

            save_work_progress_entries(report, request.POST)
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

            messages.success(request, "Daily report updated successfully.")
            return redirect("daily_report_edit", pk=report.pk)

        for error in validation_errors:
            messages.error(request, error)

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
        "work_progress_history": report.work_progress_items.all().order_by("-id"),
        "mode": "edit",
        "changed_fields": changed_fields,
        "change_logs": report.change_logs.all()[:20],
        "can_pm_review": can_pm_review_report(request.user, report),
        **get_master_code_context(),
        **formsets,
    }

    return render(request, DAILY_REPORT_FORM_TEMPLATE, context)


@login_required
def daily_report_review(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if not can_pm_review_report(request.user, report):
        raise PermissionDenied("You are not allowed to perform Project Manager review actions on this report.")

    context = {
        "page_title": "Daily Report Review",
        "report": report,
        "can_pm_review": can_pm_review_report(request.user, report),
        "work_progress_items": get_related_items(report, "workprogress"),
        "blocked_issue_items": get_related_items(report, "blockedissue"),
        "site_visit_items": get_related_items(report, "sitevisit"),
        "workforce_items": get_related_items(report, "workforce"),
        "equipment_items": get_related_items(report, "equipment"),
        "material_items": get_related_items(report, "material"),
        "attachment_items": get_related_items(report, "attachment"),
    }

    return render(request, DAILY_REPORT_REVIEW_TEMPLATE, context)


@login_required
def daily_report_print(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    context = {
        "page_title": "Daily Report Print",
        "report": report,
        "can_pm_review": can_pm_review_report(request.user, report),
        "work_progress_items": get_related_items(report, "workprogress"),
        "blocked_issue_items": get_related_items(report, "blockedissue"),
        "site_visit_items": get_related_items(report, "sitevisit"),
        "workforce_items": get_related_items(report, "workforce"),
        "equipment_items": get_related_items(report, "equipment"),
        "material_items": get_related_items(report, "material"),
        "attachment_items": get_related_items(report, "attachment"),
    }

    return render(request, DAILY_REPORT_PRINT_TEMPLATE, context)


@login_required
@transaction.atomic
def daily_report_submit(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if report.created_by_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied("Only the report creator can submit this report.")

    if report.status not in [DailyReport.STATUS_DRAFT, DailyReport.STATUS_RETURNED]:
        messages.error(request, "Only draft or returned reports can be submitted.")
        return redirect("daily_report_edit", pk=report.pk)

    report.status = DailyReport.STATUS_SUBMITTED
    report.submitted_at = timezone.now()
    report.save(update_fields=["status", "submitted_at", "updated_at"])

    messages.success(request, "Daily report submitted for Project Manager review.")
    return redirect("daily_report_edit", pk=report.pk)


@login_required
@transaction.atomic
def daily_report_approve(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if not can_pm_review_report(request.user, report):
        raise PermissionDenied("You are not allowed to approve this report.")

    if request.method == "POST":
        report.status = DailyReport.STATUS_APPROVED
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.review_note = request.POST.get("review_note", "").strip()
        report.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ])

        messages.success(request, "Daily report approved successfully.")

    return redirect("daily_report_review", pk=report.pk)


@login_required
@transaction.atomic
def daily_report_return(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if not can_pm_review_report(request.user, report):
        raise PermissionDenied("You are not allowed to return this report.")

    if request.method == "POST":
        note = request.POST.get("review_note", "").strip()

        if not note:
            messages.error(request, "Return note is required.")
            return redirect("daily_report_review", pk=report.pk)

        report.status = DailyReport.STATUS_RETURNED
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.review_note = note
        report.returned_count += 1
        report.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "returned_count",
            "updated_at",
        ])

        messages.success(request, "Daily report returned for correction.")

    return redirect("daily_report_review", pk=report.pk)


@login_required
@transaction.atomic
def daily_report_reject(request, pk):
    report = get_object_or_404(DailyReport, pk=pk)
    check_report_permission(request.user, report)

    if not can_pm_review_report(request.user, report):
        raise PermissionDenied("You are not allowed to reject this report.")

    if request.method == "POST":
        note = request.POST.get("review_note", "").strip()

        if not note:
            messages.error(request, "Rejection note is required.")
            return redirect("daily_report_review", pk=report.pk)

        report.status = DailyReport.STATUS_REJECTED
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.review_note = note
        report.save(update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ])

        messages.success(request, "Daily report rejected.")

    return redirect("daily_report_review", pk=report.pk)


@login_required
def blocked_issue_list(request):
    if not can_view_blocked_issues(request.user):
        raise PermissionDenied("You do not have permission to view blocked issues.")

    issues = BlockedIssue.objects.select_related(
        "daily_report",
        "daily_report__project",
        "daily_report__created_by",
    )

    assigned_projects = get_assigned_projects(request.user)

    if is_site_engineer(request.user):
        issues = issues.filter(
            daily_report__project__in=assigned_projects
        )

    elif user_in_group(request.user, "Project_mgr"):
        pm_projects = get_assigned_projects(
            request.user,
            role=ProjectAssignment.ROLE_PROJECT_MANAGER,
        )
        issues = issues.filter(
            daily_report__project__in=pm_projects
        )

    elif is_department_manager(request.user):
        issues = issues.filter(
            pm_status__in=[
                BlockedIssue.STATUS_ESCALATED,
                BlockedIssue.STATUS_PM_REVIEW,
                BlockedIssue.STATUS_OPEN,
            ]
        )

    elif request.user.is_superuser or user_in_group(request.user, "Admin"):
        pass

    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")
    project_id = request.GET.get("project", "")

    if status_filter:
        issues = issues.filter(pm_status=status_filter)

    if priority_filter:
        if any(field.name == "priority" for field in BlockedIssue._meta.fields):
            issues = issues.filter(priority__iexact=priority_filter)

    if project_id:
        issues = issues.filter(daily_report__project_id=project_id)

    issues = issues.order_by("-created_at")

    projects = (
        DailyReport.objects
        .filter(blocked_issues__in=issues)
        .exclude(project__isnull=True)
        .values("project_id", "project__name")
        .distinct()
        .order_by("project__name")
    )

    open_blocked_issues_count = issues.exclude(
        pm_status=BlockedIssue.STATUS_CLOSED
    ).count()

    submitted_reports_count = (
        DailyReport.objects
        .filter(
            blocked_issues__in=issues,
            status=DailyReport.STATUS_SUBMITTED,
        )
        .distinct()
        .count()
    )

    context = {
        "page_title": "Blocked Issues Center",
        "issues": issues,
        "projects": projects,
        "selected_status": status_filter,
        "selected_priority": priority_filter,
        "selected_project": project_id,
        "status_choices": getattr(BlockedIssue, "STATUS_CHOICES", []),
        "can_manage_blocked_issues": can_manage_blocked_issues(request.user),
        "open_blocked_issues_count": open_blocked_issues_count,
        "submitted_reports_count": submitted_reports_count,
    }

    return render(request, "reports/blocked_issues/blocked_issue_list.html", context)


@login_required
@transaction.atomic
def blocked_issue_detail(request, pk):
    if not can_view_blocked_issues(request.user):
        raise PermissionDenied("You do not have permission to view this blocked issue.")

    issue = get_object_or_404(
        BlockedIssue.objects.select_related(
            "daily_report",
            "daily_report__project",
            "daily_report__created_by",
        ),
        pk=pk,
    )

    # Site Engineer can only view blocked issues for assigned projects.
    if is_site_engineer(request.user):
        assigned_projects = get_assigned_projects(
            request.user,
            role=ProjectAssignment.ROLE_SITE_ENGINEER,
        )
        if not assigned_projects.filter(pk=issue.daily_report.project_id).exists():
            raise PermissionDenied("You can only view blocked issues for your assigned projects.")

    # Project Manager can only view/manage assigned project issues.
    if is_project_manager(request.user):
        pm_projects = get_assigned_projects(
            request.user,
            role=ProjectAssignment.ROLE_PROJECT_MANAGER,
        )
        if not pm_projects.filter(pk=issue.daily_report.project_id).exists():
            raise PermissionDenied("You can only manage blocked issues for your assigned projects.")

    if request.method == "POST":
        if not can_manage_blocked_issues(request.user):
            raise PermissionDenied("Only Project Manager or Department Manager can update blocked issue decisions.")

        safe_set_attr(
            issue,
            "pm_status",
            request.POST.get("pm_status", getattr(issue, "pm_status", "")),
        )
        safe_set_attr(issue, "priority", request.POST.get("priority", "").strip())
        safe_set_attr(issue, "responsible_party", request.POST.get("responsible_party", "").strip())
        safe_set_attr(issue, "follow_up_with", request.POST.get("follow_up_with", "").strip())
        safe_set_attr(issue, "impact", request.POST.get("impact", "").strip())
        safe_set_attr(issue, "impact_note", request.POST.get("impact_note", "").strip())
        safe_set_attr(issue, "amended_solution", request.POST.get("amended_solution", "").strip())
        safe_set_attr(issue, "suggested_solution", request.POST.get("suggested_solution", "").strip())
        safe_set_attr(issue, "pm_note", request.POST.get("pm_note", "").strip())
        safe_set_attr(issue, "reviewed_by", request.user)
        safe_set_attr(issue, "reviewed_at", timezone.now())

        status_value = getattr(issue, "pm_status", "")
        closed_values = [
            getattr(BlockedIssue, "STATUS_RESOLVED", "resolved"),
            getattr(BlockedIssue, "STATUS_CLOSED", "closed"),
        ]

        if status_value in closed_values:
            safe_set_attr(issue, "resolved_at", timezone.now())

        issue.save()

        messages.success(request, "Blocked issue updated successfully.")
        return redirect("blocked_issue_detail", pk=issue.pk)

    context = {
        "page_title": "Blocked Issue Details",
        "issue": issue,
        "status_choices": getattr(BlockedIssue, "STATUS_CHOICES", []),
        "can_manage_blocked_issues": can_manage_blocked_issues(request.user),
    }

    return render(request, "reports/blocked_issues/blocked_issue_detail.html", context)
