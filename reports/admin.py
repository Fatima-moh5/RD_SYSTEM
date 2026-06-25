from reports.master_data.admin import *

from django.contrib import admin

from reports.models import DailyReportAttachment
from reports.models import UserActivityLog

@admin.register(DailyReportAttachment)
class DailyReportAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "daily_report",
        "document_type",
        "description",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "document_type",
        "uploaded_at",
        "uploaded_by",
    )

    search_fields = (
        "document_type",
        "description",
        "daily_report__project__name",
    )

    readonly_fields = (
        "uploaded_at",
    )

    ordering = (
        "-uploaded_at",
    )

    @admin.register(UserActivityLog)
    class UserActivityLogAdmin(admin.ModelAdmin):

        list_display = (
            "id",
            "user",
            "action",
            "ip_address",
            "created_at",
        )

        list_filter = (
            "action",
            "created_at",
        )

        search_fields = (
            "user__username",
            "description",
        )

        readonly_fields = (
            "created_at",
        )

        ordering = (
            "-created_at",
        )
from reports.models import WorkerProfile
