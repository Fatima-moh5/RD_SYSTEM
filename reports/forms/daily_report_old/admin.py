from django.contrib import admin

from .models import (
    Daily_Report,
    WorkProgress,
    BlockedIssue,
    SiteVisit,
    WorkforceEntry,
    EquipmentUsage,
    MaterialReceipt,
    DailyReportChangeLog,
)


class WorkProgressInline(admin.TabularInline):
    model = WorkProgress
    extra = 0


class BlockedIssueInline(admin.TabularInline):
    model = BlockedIssue
    extra = 0


class SiteVisitInline(admin.TabularInline):
    model = SiteVisit
    extra = 0


class WorkforceEntryInline(admin.TabularInline):
    model = WorkforceEntry
    extra = 0


class EquipmentUsageInline(admin.TabularInline):
    model = EquipmentUsage
    extra = 0


class MaterialReceiptInline(admin.TabularInline):
    model = MaterialReceipt
    extra = 0


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "reference_date",
        "created_by",
        "status",
        "weather_condition",
        "temperature",
        "weather_source",
        "weather_confirmed",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "project",
        "reference_date",
        "created_by",
        "weather_source",
        "weather_confirmed",
    )

    search_fields = (
        "project__name",
        "project__code",
        "created_by__username",
        "weather_condition",
        "general_notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        WorkProgressInline,
        BlockedIssueInline,
        SiteVisitInline,
        WorkforceEntryInline,
        EquipmentUsageInline,
        MaterialReceiptInline,
    ]


@admin.register(DailyReportChangeLog)
class DailyReportChangeLogAdmin(admin.ModelAdmin):
    list_display = (
        "report",
        "field_name",
        "old_value",
        "new_value",
        "edited_by",
        "edited_at",
    )

    list_filter = (
        "edited_at",
        "edited_by",
    )

    search_fields = (
        "field_name",
        "old_value",
        "new_value",
        "edited_by__username",
    )

    readonly_fields = (
        "report",
        "field_name",
        "old_value",
        "new_value",
        "edited_by",
        "edited_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False