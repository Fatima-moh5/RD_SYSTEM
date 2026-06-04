from django.urls import path
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from reports.views import home_view, dashboard_home, logout_view, feedback_view, forgot_password_view
from reports.views import home_view, dashboard_home, logout_view

from reports.api_views import (
    master_code_builder_options,
    project_areas_options,
    fetch_project_weather,
)

from reports.views_modules.daily_report_views import (
    daily_report_list,
    daily_report_create,
    daily_report_edit,
    daily_report_review,
    daily_report_print,
    daily_report_submit,
    daily_report_approve,
    daily_report_return,
    daily_report_reject,
    blocked_issue_list,
    blocked_issue_detail,
)

from reports.views import (
    home_view,
    dashboard_home,
    logout_view,
    feedback_view,
    forgot_password_view,
    admin_activity_log_view,
)

urlpatterns = [

path("admin-activity-log/", admin_activity_log_view, name="admin_activity_log"),

    # LOGIN PAGE
    path("", home_view, name="home"),

    # LOGOUT
    path("logout/", logout_view, name="logout"),
    
    path("feedback/", feedback_view, name="feedback"),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("daily-reports/<int:pk>/submit/", daily_report_submit, name="daily_report_submit"),
    path("daily-reports/<int:pk>/approve/", daily_report_approve, name="daily_report_approve"),
    path("daily-reports/<int:pk>/return/", daily_report_return, name="daily_report_return"),
    path("daily-reports/<int:pk>/reject/", daily_report_reject, name="daily_report_reject"),
    path(
        "change-password/",
        PasswordChangeView.as_view(
            template_name="accounts/change_password.html",
            success_url="/change-password/done/"
        ),
        name="change_password"
    ),

    path(
        "blocked-issues/",
        blocked_issue_list,
        name="blocked_issue_list"
    ),

    path(
        "blocked-issues/<int:pk>/",
        blocked_issue_detail,
        name="blocked_issue_detail"
    ),
    path(
        "change-password/done/",
        PasswordChangeDoneView.as_view(
            template_name="accounts/change_password_done.html"
        ),
        name="password_change_done"
    ),
    # DASHBOARD
    path("dashboard/", dashboard_home, name="dashboard_home"),

    # DAILY REPORTS
    path("daily-reports/", daily_report_list, name="daily_report_list"),

    path(
            "daily-reports/create/",
            daily_report_create,
            name="daily_report_create"
        ),

    path(
            "daily-reports/<int:pk>/edit/",
            daily_report_edit,
            name="daily_report_edit"
        ),

    path(
            "daily-reports/<int:pk>/review/",
            daily_report_review,
            name="daily_report_review"
        ),

    path(
            "daily-reports/<int:pk>/print/",
            daily_report_print,
            name="daily_report_print"
        ),

    # APIs
    path(
        "api/master-code-builder-options/",
        master_code_builder_options,
        name="master_code_builder_options"
    ),

    path(
        "api/project-areas-options/",
        project_areas_options,
        name="project_areas_options"
    ),

    path(
        "api/fetch-project-weather/",
        fetch_project_weather,
        name="fetch_project_weather"
    ),
]