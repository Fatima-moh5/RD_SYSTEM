from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)

    site_engineer = models.CharField(max_length=255, blank=True, null=True)
    project_manager = models.CharField(max_length=255, blank=True, null=True)

    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    permit_id = models.CharField(max_length=100, blank=True, null=True)
    permit_category = models.CharField(max_length=100, blank=True, null=True)
    authority = models.CharField(max_length=255, blank=True, null=True)
    project_description = models.TextField(blank=True, null=True)

    building_floors_count = models.PositiveIntegerField(blank=True, null=True)

    latitude = models.DecimalField(max_digits=18, decimal_places=16, blank=True, null=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=16, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_project_floors()

    def sync_project_floors(self):
        """
        Automatically create/update standard floor areas based on building_floors_count.

        Example:
        building_floors_count = 5

        Generated areas:
        F01 - Floor 1
        F02 - Floor 2
        F03 - Floor 3
        F04 - Floor 4
        F05 - Floor 5
        """
        floor_count = self.building_floors_count or 0

        if floor_count <= 0:
            return

        for floor_number in range(1, floor_count + 1):
            code = f"F{floor_number:02d}"
            name = f"Floor {floor_number}"

            ProjectArea.objects.update_or_create(
                project=self,
                code=code,
                defaults={
                    "name": name,
                    "area_type": ProjectArea.AREA_FLOOR,
                    "sort_order": floor_number,
                    "is_active": True,
                },
            )


class ProjectAssignment(models.Model):
    ROLE_SITE_ENGINEER = "site_engineer"
    ROLE_PROJECT_MANAGER = "project_manager"
    ROLE_DEPARTMENT_MANAGER = "department_manager"
    ROLE_OPERATION = "operation"
    ROLE_COST_CONTROL = "cost_control"

    ROLE_CHOICES = [
        (ROLE_SITE_ENGINEER, "Site Engineer"),
        (ROLE_PROJECT_MANAGER, "Project Manager"),
        (ROLE_DEPARTMENT_MANAGER, "Department Manager"),
        (ROLE_OPERATION, "Operation / Back Office"),
        (ROLE_COST_CONTROL, "Cost Control"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_assignments",
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project__code", "role", "user__username"]
        unique_together = ("project", "user", "role")
        verbose_name = "Project Assignment"
        verbose_name_plural = "Project Assignments"

    def __str__(self):
        return f"{self.project} / {self.user} / {self.get_role_display()}"


class ProjectArea(models.Model):
    AREA_BASEMENT = "basement"
    AREA_FLOOR = "floor"
    AREA_ROOF = "roof"
    AREA_EXTERNAL = "external"
    AREA_PARKING = "parking"
    AREA_COMMON = "common"
    AREA_OTHER = "other"

    AREA_TYPE_CHOICES = [
        (AREA_BASEMENT, "Basement"),
        (AREA_FLOOR, "Floor"),
        (AREA_ROOF, "Roof"),
        (AREA_EXTERNAL, "External Area"),
        (AREA_PARKING, "Parking"),
        (AREA_COMMON, "Common Area"),
        (AREA_OTHER, "Other"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="areas",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    area_type = models.CharField(
        max_length=30,
        choices=AREA_TYPE_CHOICES,
        default=AREA_FLOOR,
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["project__code", "sort_order", "code"]
        unique_together = ("project", "code")
        verbose_name = "Project Area"
        verbose_name_plural = "Project Areas"

    def __str__(self):
        return f"{self.project.code} - {self.code} - {self.name}"


class ProjectPhase(models.Model):
    phase_code = models.CharField(max_length=10, unique=True)
    phase_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "phase_code"]
        verbose_name = "Project Phase"
        verbose_name_plural = "Project Phases"

    def __str__(self):
        return self.phase_code


class DocumentType(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["symbol"]
        verbose_name = "Document Type"
        verbose_name_plural = "Document Types"

    def __str__(self):
        return self.symbol


class Category(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["symbol"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.symbol


class Subcategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="subcategories",
    )
    symbol = models.CharField(max_length=10)
    description = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__symbol", "symbol"]
        unique_together = ("category", "symbol")
        verbose_name = "Subcategory"
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return self.symbol


class MasterCode(models.Model):
    project_phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.PROTECT,
        related_name="master_codes",
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="master_codes",
        blank=True,
        null=True,
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="master_codes",
        blank=True,
        null=True,
    )

    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [
            "project_phase__display_order",
            "category__symbol",
            "subcategory__symbol",
        ]
        unique_together = (
            "project_phase",
            "category",
            "subcategory",
        )
        verbose_name = "Master Code"
        verbose_name_plural = "Master Codes"

    def clean(self):
        if self.subcategory and self.category:
            if self.subcategory.category_id != self.category_id:
                raise ValidationError(
                    "Selected subcategory does not belong to the selected category."
                )

        if not self.project_phase or not self.category or not self.subcategory:
            raise ValidationError(
                "Project phase, category, and subcategory are required."
            )

    def save(self, *args, **kwargs):
        if self.project_phase and self.category and self.subcategory:
            self.code = (
                f"{self.project_phase.phase_code}-"
                f"{self.category.symbol}-"
                f"{self.subcategory.symbol}"
            )

        if not self.description and self.project_phase and self.category and self.subcategory:
            self.description = (
                f"{self.project_phase.phase_name} / "
                f"{self.category.description} / "
                f"{self.subcategory.description}"
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.code and self.description:
            return f"{self.code} - {self.description}"
        return self.code or "Master Code"


class EquipmentMaster(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    owner = models.CharField(max_length=100, blank=True, null=True)
    supplier = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default="Available")

    def __str__(self):
        return self.name


class LookupItem(models.Model):
    LIST_TYPES = [
        ("qc_result", "QC Result"),
        ("severity", "Severity"),
        ("followup", "Follow Up"),
        ("workforce", "Workforce"),
        ("skill_level", "Skill Level"),
        ("usage_type", "Usage Type"),
        ("uom", "UOM"),
        ("status", "Status"),
        ("visit_type", "Visit Type"),
        ("site_visit_code", "Site Visit Code"),
        ("issue_priority", "Issue Priority"),
        ("issue_status", "Issue Status"),
    ]

    list_type = models.CharField(max_length=50, choices=LIST_TYPES)
    value = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["list_type", "sort_order", "value"]

    def __str__(self):
        return f"{self.get_list_type_display()} - {self.value}"