from django.contrib import admin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import include, path


def logout_view(request):
    logout(request)
    return redirect("/admin/login/")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("logout/", logout_view, name="logout"),
    path("", include("reports.urls")),
]