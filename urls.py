from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # =========================================
    # Django Admin
    # =========================================
    path("admin/", admin.site.urls),

    # =========================================
    # Reports App URLs
    # =========================================
    path("", include("reports.urls")),
]