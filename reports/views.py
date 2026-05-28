from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reports.master_data.models import Project, ProjectAssignment
from reports.models import DailyReport, BlockedIssue, UserActivityLog


GROUP_SITE_ENGINEER = "site_eng"
GROUP_PROJECT_MANAGER = "Project_mgr"
GROUP_COST_CONTROL = "Cost_Control"
GROUP_DEPARTMENT_MANAGER = "dep_mgr"
GROUP_OPERATIONS = "operations"
GROUP_ADMIN = "Admin"


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def log_user_activity(request, action, description=""):
    UserActivityLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        description=description,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


def get_user_role_label(user):
    if user_in_group(user, GROUP_PROJECT_MANAGER):
        return "Project Manager"

    if user_in_group(user, GROUP_COST_CONTROL):
        return "Cost Control"

    if user_in_group(user, GROUP_DEPARTMENT_MANAGER):
        return "Department Manager"

    if user_in_group(user, GROUP_OPERATIONS):
        return "Operations"

    if user_in_group(user, GROUP_SITE_ENGINEER):
        return "Site Engineer"

    if user.is_superuser or user_in_group(user, GROUP_ADMIN):
        return "Admin"

    return "User"


def get_assigned_projects_for_dashboard(user, role=None):
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


def get_project_manager_projects(user):
    """
    Returns projects assigned to the current Project Manager.

    Superusers/Admin users can see all active projects.
    Project Managers see only projects where they are assigned as Project Manager.
    """
    if user.is_superuser or user_in_group(user, GROUP_ADMIN):
        return Project.objects.filter(is_active=True)

    return get_assigned_projects_for_dashboard(
        user,
        role=ProjectAssignment.ROLE_PROJECT_MANAGER,
    )


def get_open_blocked_issues_queryset(projects=None, created_by=None):
    """
    Shared open blocked issue filter.

    Open means any blocked issue that is not closed by the PM workflow.
    """
    qs = BlockedIssue.objects.select_related(
        "daily_report",
        "daily_report__project",
        "daily_report__created_by",
        "reviewed_by",
    ).exclude(
        pm_status=BlockedIssue.STATUS_CLOSED
    )

    if projects is not None:
        qs = qs.filter(daily_report__project__in=projects)

    if created_by is not None:
        qs = qs.filter(daily_report__created_by=created_by)

    return qs



def user_can_manage_blocked_issues(user):
    return (
        user.is_superuser
        or user_in_group(user, GROUP_ADMIN)
        or user_in_group(user, GROUP_PROJECT_MANAGER)
    )


def model_has_field(model_class, field_name):
    try:
        model_class._meta.get_field(field_name)
        return True
    except Exception:
        return False


def set_field_if_exists(instance, field_name, value, update_fields):
    if model_has_field(instance.__class__, field_name):
        setattr(instance, field_name, value)
        update_fields.append(field_name)


def get_pm_allowed_blocked_issues(user):
    """
    Project Manager/Admin scope for Blocked Issues Center.
    PM sees issues only for assigned PM projects.
    Admin/superuser sees all active project issues.
    """
    projects = get_project_manager_projects(user)
    qs = get_open_blocked_issues_queryset(projects=projects)
    return qs, projects


def home_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            log_user_activity(
                request,
                UserActivityLog.ACTION_LOGIN,
                "User logged into RD_SYSTEM.",
            )

            messages.success(request, "Welcome back.")
            return redirect("dashboard_home")

        messages.error(request, "Invalid username or password.")

    return render(request, "home.html")


def logout_view(request):
    if request.user.is_authenticated:
        log_user_activity(
            request,
            UserActivityLog.ACTION_LOGOUT,
            "User logged out from RD_SYSTEM.",
        )

    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def feedback_view(request):
    if request.method == "POST":
        messages.success(request, "Thank you. Your feedback has been received.")
        return redirect("home")

    return render(request, "accounts/feedback.html")


def forgot_password_view(request):
    if request.method == "POST":
        messages.success(
            request,
            "Your password reset request has been received. Please contact the system administrator.",
        )
        return redirect("home")

    return render(request, "accounts/forgot_password.html")


@login_required
def dashboard_home(request):
    role_label = get_user_role_label(request.user)
    today = timezone.localdate()

    my_blocked_issues = []
    open_blocked_issues_count = 0
    returned_reports = []

    if role_label == "Site Engineer":
        assigned_projects = get_assigned_projects_for_dashboard(
            request.user,
            role=ProjectAssignment.ROLE_SITE_ENGINEER,
        )

        reports = DailyReport.objects.select_related(
            "project",
            "created_by",
        ).filter(
            Q(created_by=request.user) | Q(project__in=assigned_projects)
        ).distinct()

        today_report = reports.filter(reference_date=today).first()

        pending_reports_count = reports.filter(
            Q(status=DailyReport.STATUS_DRAFT)
            | Q(status=DailyReport.STATUS_SUBMITTED)
        ).count()

        returned_reports_count = reports.filter(
            status=DailyReport.STATUS_RETURNED
        ).count()

        submitted_reports_count = reports.filter(
            status=DailyReport.STATUS_SUBMITTED
        ).count()

        latest_reports = reports.order_by("-reference_date", "-id")[:5]

        returned_reports = reports.filter(
            status=DailyReport.STATUS_RETURNED
        ).order_by("-updated_at")[:5]

        open_blocked_issues_qs = get_open_blocked_issues_queryset(
            created_by=request.user
        )

        my_blocked_issues = open_blocked_issues_qs.order_by("-updated_at")[:5]
        open_blocked_issues_count = open_blocked_issues_qs.count()

        action_items = []

        if not today_report:
            action_items.append({
                "title": "Today’s daily report is not created yet",
                "status": "Required Today",
                "action": "Create Report",
                "url_name": "daily_report_create",
                "priority": "high",
            })

        if returned_reports_count > 0:
            action_items.append({
                "title": f"{returned_reports_count} returned report(s) need correction",
                "status": "Needs Correction",
                "action": "Open Reports",
                "url_name": "daily_report_list",
                "priority": "medium",
            })

        if open_blocked_issues_count > 0:
            action_items.append({
                "title": f"{open_blocked_issues_count} blocked issue(s) need follow-up",
                "status": "Follow-up",
                "action": "Open Issues",
                "url_name": "blocked_issue_list",
                "priority": "medium",
            })

    else:
        if role_label == "Project Manager" or role_label == "Admin" or request.user.is_superuser:
            assigned_projects = get_project_manager_projects(request.user)
            reports = DailyReport.objects.select_related(
                "project",
                "created_by",
            ).filter(
                project__in=assigned_projects
            ).distinct()
        else:
            assigned_projects = Project.objects.none()
            reports = DailyReport.objects.select_related(
                "project",
                "created_by",
            ).all()

        today_report = None

        pending_reports_count = reports.filter(
            status=DailyReport.STATUS_SUBMITTED
        ).count()

        returned_reports_count = reports.filter(
            status=DailyReport.STATUS_RETURNED
        ).count()

        submitted_reports_count = reports.filter(
            status=DailyReport.STATUS_SUBMITTED
        ).count()

        latest_reports = reports.order_by("-reference_date", "-id")[:5]

        if role_label == "Project Manager" or role_label == "Admin" or request.user.is_superuser:
            open_blocked_issues_qs = get_open_blocked_issues_queryset(
                projects=assigned_projects
            )
            my_blocked_issues = open_blocked_issues_qs.order_by("-updated_at")[:5]
            open_blocked_issues_count = open_blocked_issues_qs.count()

        action_items = []

        if submitted_reports_count > 0:
            action_items.append({
                "title": f"{submitted_reports_count} daily report(s) awaiting review",
                "status": "Needs PM Review",
                "action": "Review Reports",
                "url_name": "daily_report_list",
                "priority": "high",
            })

        if open_blocked_issues_count > 0:
            action_items.append({
                "title": f"{open_blocked_issues_count} blocked issue(s) need PM decision",
                "status": "Needs Solution",
                "action": "Open Center",
                "url_name": "blocked_issue_list",
                "priority": "high",
            })

    context = {
        "role_label": role_label,
        "today": today,
        "assigned_projects": assigned_projects,
        "assigned_projects_count": assigned_projects.count(),
        "today_report": today_report,
        "pending_reports_count": pending_reports_count,
        "returned_reports_count": returned_reports_count,
        "submitted_reports_count": submitted_reports_count,
        "latest_reports": latest_reports,
        "action_items": action_items,
        "my_blocked_issues": my_blocked_issues,
        "open_blocked_issues_count": open_blocked_issues_count,
        "returned_reports": returned_reports,
    }

    if user_in_group(request.user, GROUP_PROJECT_MANAGER):
        return render(request, "dashboard/project_manager_dashboard.html", context)

    if user_in_group(request.user, GROUP_COST_CONTROL):
        return render(request, "dashboard/cost_control_dashboard.html", context)

    if user_in_group(request.user, GROUP_DEPARTMENT_MANAGER):
        return render(request, "dashboard/department_manager_dashboard.html", context)

    if user_in_group(request.user, GROUP_OPERATIONS):
        return render(request, "dashboard/operations_dashboard.html", context)

    if user_in_group(request.user, GROUP_SITE_ENGINEER):
        return render(request, "dashboard/site_engineer_dashboard.html", context)

    if request.user.is_superuser or user_in_group(request.user, GROUP_ADMIN):
        return render(request, "dashboard/project_manager_dashboard.html", context)

    return render(request, "dashboard/site_engineer_dashboard.html", context)


@login_required
def admin_activity_log_view(request):
    if not request.user.is_superuser and not user_in_group(request.user, GROUP_ADMIN):
        raise PermissionDenied("Only admin users can view activity logs.")

    logs = UserActivityLog.objects.select_related("user").all()[:200]

    context = {
        "role_label": get_user_role_label(request.user),
        "today": timezone.localdate(),
        "logs": logs,
    }

    return render(request, "dashboard/admin_activity_log.html", context)



@login_required
def blocked_issue_list(request):
    """
    Project Manager Blocked Issues Center.

    IMPORTANT:
    This version is safe with your CURRENT BlockedIssue model.
    It does NOT assume that fields like severity, impact, solution, or assigned_to exist.
    """
    if not user_can_manage_blocked_issues(request.user):
        raise PermissionDenied("Only Project Manager/Admin users can access Blocked Issues Center.")

    role_label = get_user_role_label(request.user)
    today = timezone.localdate()
    assigned_projects = get_project_manager_projects(request.user)

    qs = BlockedIssue.objects.select_related(
        "daily_report",
        "daily_report__project",
        "daily_report__created_by",
        "reviewed_by",
    ).filter(
        daily_report__project__in=assigned_projects
    )

    status_filter = request.GET.get("status", "open").strip() or "open"
    project_filter = request.GET.get("project", "").strip()
    severity_filter = request.GET.get("severity", "").strip()

    has_pm_status = model_has_field(BlockedIssue, "pm_status")
    has_severity = model_has_field(BlockedIssue, "severity")

    if has_pm_status:
        if status_filter == "closed":
            qs = qs.filter(pm_status=BlockedIssue.STATUS_CLOSED)
        elif status_filter == "all":
            pass
        else:
            qs = qs.exclude(pm_status=BlockedIssue.STATUS_CLOSED)
            status_filter = "open"
    else:
        status_filter = "all"

    if project_filter:
        qs = qs.filter(daily_report__project_id=project_filter)

    if has_severity and severity_filter:
        qs = qs.filter(severity=severity_filter)
    else:
        severity_filter = ""

    qs = qs.order_by("-daily_report__reference_date", "-id")

    all_project_issues = BlockedIssue.objects.filter(
        daily_report__project__in=assigned_projects
    )

    if has_pm_status:
        open_blocked_issues_count = all_project_issues.exclude(
            pm_status=BlockedIssue.STATUS_CLOSED
        ).count()
        closed_blocked_issues_count = all_project_issues.filter(
            pm_status=BlockedIssue.STATUS_CLOSED
        ).count()
    else:
        open_blocked_issues_count = all_project_issues.count()
        closed_blocked_issues_count = 0

    severity_choices = []
    if has_severity:
        severity_choices = BlockedIssue._meta.get_field("severity").choices

    status_choices = []
    if has_pm_status:
        status_choices = BlockedIssue._meta.get_field("pm_status").choices

    issues = []
    for issue in qs:
        report = getattr(issue, "daily_report", None)
        project = getattr(report, "project", None) if report else None
        reporter = getattr(report, "created_by", None) if report else None

        reporter_name = "-"
        if reporter:
            reporter_name = reporter.get_full_name() or reporter.username

        issue_title = "Blocked issue"
        if getattr(issue, "master_code", None):
            issue_title = str(issue.master_code)

        issue_notes = (
            getattr(issue, "notes", "")
            or getattr(issue, "description", "")
            or getattr(issue, "issue_description", "")
            or "-"
        )

        severity_display = "Open Issue"
        if has_severity:
            try:
                severity_display = issue.get_severity_display()
            except Exception:
                severity_display = getattr(issue, "severity", "Open Issue") or "Open Issue"

        pm_status_value = getattr(issue, "pm_status", "") if has_pm_status else ""
        pm_status_display = "Open"
        if has_pm_status:
            try:
                pm_status_display = issue.get_pm_status_display()
            except Exception:
                pm_status_display = pm_status_value or "Open"

        issues.append({
            "id": issue.id,
            "date": getattr(report, "reference_date", None) if report else None,
            "project": project or "-",
            "reported_by": reporter_name,
            "severity_display": severity_display,
            "title": issue_title,
            "notes": issue_notes,
            "follow_up_with": getattr(issue, "follow_up_with", "") or "",
            "pm_status": pm_status_value,
            "pm_status_display": pm_status_display,
            "impact": getattr(issue, "impact", "") or getattr(issue, "pm_impact", "") or "",
            "responsible_person": getattr(issue, "responsible_person", "") or getattr(issue, "assigned_to", "") or "",
            "amended_solution": getattr(issue, "amended_solution", "") or getattr(issue, "solution", "") or "",
            "pm_notes": getattr(issue, "pm_notes", "") or getattr(issue, "review_notes", "") or "",
        })

    context = {
        "role_label": role_label,
        "today": today,
        "assigned_projects": assigned_projects,
        "issues": issues,
        "status_filter": status_filter,
        "severity_filter": severity_filter,
        "project_filter": project_filter,
        "severity_choices": severity_choices,
        "status_choices": status_choices,
        "has_severity": has_severity,
        "has_pm_status": has_pm_status,
        "open_blocked_issues_count": open_blocked_issues_count,
        "closed_blocked_issues_count": closed_blocked_issues_count,
        "action_items": [],
    }

    return render(request, "reports/blocked_issues/blocked_issue_list.html", context)


@login_required
def blocked_issue_update(request, pk):
    """
    PM update action for one blocked issue.

    Safe with the current model:
    - Updates only fields that really exist.
    - Does not crash if future PM fields are not created yet.
    """
    if not user_can_manage_blocked_issues(request.user):
        raise PermissionDenied("Only Project Manager/Admin users can update blocked issues.")

    assigned_projects = get_project_manager_projects(request.user)

    issue = get_object_or_404(
        BlockedIssue.objects.select_related("daily_report", "daily_report__project"),
        pk=pk,
        daily_report__project__in=assigned_projects,
    )

    if request.method != "POST":
        return redirect("blocked_issue_list")

    update_fields = []

    if model_has_field(BlockedIssue, "pm_status"):
        pm_status = request.POST.get("pm_status", "").strip()
        allowed_statuses = [choice[0] for choice in BlockedIssue._meta.get_field("pm_status").choices]
        if pm_status and (not allowed_statuses or pm_status in allowed_statuses):
            issue.pm_status = pm_status
            update_fields.append("pm_status")

    impact_value = request.POST.get("impact", "").strip()
    responsible_value = request.POST.get("responsible_person", "").strip()
    solution_value = request.POST.get("amended_solution", "").strip()
    notes_value = request.POST.get("pm_notes", "").strip()

    set_field_if_exists(issue, "impact", impact_value, update_fields)
    set_field_if_exists(issue, "pm_impact", impact_value, update_fields)
    set_field_if_exists(issue, "responsible_person", responsible_value, update_fields)
    set_field_if_exists(issue, "assigned_to", responsible_value, update_fields)
    set_field_if_exists(issue, "amended_solution", solution_value, update_fields)
    set_field_if_exists(issue, "solution", solution_value, update_fields)
    set_field_if_exists(issue, "pm_notes", notes_value, update_fields)
    set_field_if_exists(issue, "review_notes", notes_value, update_fields)

    if model_has_field(BlockedIssue, "reviewed_by"):
        issue.reviewed_by = request.user
        update_fields.append("reviewed_by")

    if model_has_field(BlockedIssue, "reviewed_at"):
        issue.reviewed_at = timezone.now()
        update_fields.append("reviewed_at")

    if model_has_field(BlockedIssue, "updated_at"):
        update_fields.append("updated_at")

    update_fields = list(dict.fromkeys(update_fields))

    if update_fields:
        issue.save(update_fields=update_fields)
        messages.success(request, "Blocked issue updated successfully.")
    else:
        messages.info(
            request,
            "No PM update fields exist yet in BlockedIssue model. Status page is working, but save fields need model upgrade later.",
        )

    return redirect("blocked_issue_list")
