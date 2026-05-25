from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from reports.master_data.models import (
    Project,
    ProjectPhase,
    DocumentType,
    Category,
    Subcategory,
    MasterCode,
    EquipmentMaster,
    LookupItem,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "city",
        "site_engineer",
        "project_manager",
    )
    search_fields = (
        "code",
        "name",
        "city",
        "address",
    )


@admin.register(ProjectPhase)
class ProjectPhaseAdmin(admin.ModelAdmin):
    list_display = (
        "phase_code",
        "phase_name",
        "display_order",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "phase_code",
        "phase_name",
    )
    ordering = (
        "display_order",
        "phase_code",
    )


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "description",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "symbol",
        "description",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "description",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "symbol",
        "description",
    )


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "description",
        "category",
        "is_active",
    )
    list_filter = (
        "category",
        "is_active",
    )
    search_fields = (
        "symbol",
        "description",
        "category__symbol",
        "category__description",
    )


class CleanForeignKeyWidget(ForeignKeyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        if value is None:
            return None

        value = str(value).strip().upper()

        if value == "":
            return None

        return super().clean(value, row=row, *args, **kwargs)


class SubcategoryByCategoryWidget(ForeignKeyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        sub_symbol = str(value or "").strip().upper()
        cat_symbol = str(row.get("category") or "").strip().upper()

        if not sub_symbol:
            return None

        try:
            return Subcategory.objects.get(
                symbol__iexact=sub_symbol,
                category__symbol__iexact=cat_symbol,
            )
        except Subcategory.DoesNotExist:
            raise ValueError(
                f"Subcategory not found: subcategory='{sub_symbol}', category='{cat_symbol}'"
            )


class MasterCodeResource(resources.ModelResource):

    project_phase = fields.Field(
        column_name="project_phase",
        attribute="project_phase",
        widget=ForeignKeyWidget(ProjectPhase, "id"),
    )

    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=ForeignKeyWidget(Category, "id"),
    )

    subcategory = fields.Field(
        column_name="subcategory",
        attribute="subcategory",
        widget=ForeignKeyWidget(Subcategory, "id"),
    )

    def skip_row(self, instance, original, row, import_validation_errors=None):
        code = str(row.get("code") or "").strip()
        phase = str(row.get("project_phase") or "").strip()
        category = str(row.get("category") or "").strip()
        subcategory = str(row.get("subcategory") or "").strip()

        return not any([code, phase, category, subcategory])

    def before_import_row(self, row, **kwargs):
        code = str(row.get("code") or "").strip().upper().replace("_", "-")
        phase_code = str(row.get("project_phase") or "").strip().upper()
        category_symbol = str(row.get("category") or "").strip().upper()
        subcategory_symbol = str(row.get("subcategory") or "").strip().upper()
        description = str(row.get("description") or "").strip()

        if not phase_code or not category_symbol or not subcategory_symbol:
            row["code"] = ""
            return

        project_phase = ProjectPhase.objects.get(
            phase_code__iexact=phase_code
        )

        category = Category.objects.get(
            symbol__iexact=category_symbol
        )

        subcategory, created = Subcategory.objects.get_or_create(
            category=category,
            symbol=subcategory_symbol,
            defaults={
                "description": description or subcategory_symbol,
                "is_active": True,
            },
        )

        row["code"] = code
        row["project_phase"] = project_phase.id
        row["category"] = category.id
        row["subcategory"] = subcategory.id
        row["description"] = description

    class Meta:
        model = MasterCode
        import_id_fields = ("code",)

        fields = (
            "id",
            "code",
            "project_phase",
            "category",
            "subcategory",
            "description",
            "display_order",
            "is_active",
        )

        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(MasterCode)
class MasterCodeAdmin(ImportExportModelAdmin):

    resource_class = MasterCodeResource

    list_display = (
        "code",
        "project_phase",
        "category",
        "subcategory",
        "description",
        "is_active",
    )

    list_filter = (
        "project_phase",
        "category",
        "subcategory",
        "is_active",
    )

    search_fields = (
        "code",
        "description",
        "project_phase__phase_code",
        "project_phase__phase_name",
        "category__symbol",
        "category__description",
        "subcategory__symbol",
        "subcategory__description",
    )

    readonly_fields = ("code",)

    ordering = (
        "project_phase__display_order",
        "category__symbol",
        "subcategory__symbol",
    )


@admin.register(EquipmentMaster)
class EquipmentMasterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "type",
        "owner",
        "supplier",
        "status",
    )
    list_filter = (
        "type",
        "status",
        "owner",
    )
    search_fields = (
        "code",
        "name",
        "type",
        "owner",
        "supplier",
    )


@admin.register(LookupItem)
class LookupItemAdmin(admin.ModelAdmin):
    list_display = (
        "list_type",
        "value",
        "sort_order",
        "is_active",
    )
    list_filter = (
        "list_type",
        "is_active",
    )
    search_fields = (
        "value",
    )
    ordering = (
        "list_type",
        "sort_order",
        "value",
    )