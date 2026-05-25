from reports.master_data.admin import *

from django.contrib import admin

from reports.models import DailyReportAttachment


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