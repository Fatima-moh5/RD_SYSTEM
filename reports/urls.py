from django.urls import path
from django.contrib.auth.views import LogoutView

from reports.views import home_view, dashboard_home

from reports.api_views import (
    master_code_builder_options,
    project_areas_options,
    fetch_project_weather,
)

from reports.views_modules.daily_report_views import (
    daily_report_list,
    daily_report_create,
    daily_report_edit,
    daily_report_print,
)


urlpatterns = [

    # LOGIN PAGE
    path("", home_view, name="home"),

    # LOGOUT
    path(
        "logout/",
        LogoutView.as_view(next_page="home"),
        name="logout"
    ),

    # DASHBOARD
    path("dashboard/", dashboard_home, name="dashboard_home"),

    # DAILY REPORTS
    path("daily-reports/", daily_report_list, name="daily_report_list"),
    path("daily-reports/create/", daily_report_create, name="daily_report_create"),
    path("daily-reports/<int:pk>/edit/", daily_report_edit, name="daily_report_edit"),
    path("daily-reports/<int:pk>/print/", daily_report_print, name="daily_report_print"),

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