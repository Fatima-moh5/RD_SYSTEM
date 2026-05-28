from django.conf import settings
from django.db import models
from django.utils import timezone

from reports.master_data.models import (
    Project,
    ProjectArea,
    MasterCode,
    EquipmentMaster,
    LookupItem,
)


class DailyReport(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_RETURNED = "returned"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
    (STATUS_DRAFT, "Draft"),
    (STATUS_SUBMITTED, "Submitted for Review"),
    (STATUS_APPROVED, "Approved"),
    (STATUS_RETURNED, "Returned for Correction"),
    (STATUS_REJECTED, "Rejected"),
    ]

    WEATHER_SOURCE_MANUAL = "manual"
    WEATHER_SOURCE_API_CONFIRMED = "api_confirmed"
    WEATHER_SOURCE_MANUAL_OVERRIDE = "manual_override"

    WEATHER_SOURCE_CHOICES = [
        (WEATHER_SOURCE_MANUAL, "Manual"),
        (WEATHER_SOURCE_API_CONFIRMED, "API Confirmed"),
        (WEATHER_SOURCE_MANUAL_OVERRIDE, "Manual Override"),
    ]

    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="daily_reports",
    )
    reference_date = models.DateField(default=timezone.localdate)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        blank=True,
    )

    weather_condition = models.CharField(max_length=100, blank=True, default="")
    temperature = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    weather_source = models.CharField(
        max_length=30,
        choices=WEATHER_SOURCE_CHOICES,
        default=WEATHER_SOURCE_MANUAL,
        blank=True,
    )
    weather_confirmed = models.BooleanField(default=False)
    weather_note = models.TextField(blank=True, default="")
    general_notes = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="daily_reports",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_daily_reports",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_note = models.TextField(blank=True, default="")
    returned_count = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
        ordering = ["-reference_date", "-created_at"]
        unique_together = ("project", "reference_date", "created_by")

    def __str__(self):
        project_name = self.project.name if self.project else "No Project"
        return f"{project_name} - {self.reference_date}"


class WorkProgress(models.Model):
    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="work_progress_items",
    )
    master_code = models.ForeignKey(
        MasterCode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    description = models.TextField(blank=True, default="")
    project_area = models.ForeignKey(
        ProjectArea,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="work_progress_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if self.master_code and not self.description:
            self.description = self.master_code.description or ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.description or "Active Work"


class BlockedIssue(models.Model):
    STATUS_OPEN = "open"
    STATUS_PM_REVIEW = "pm_review"
    STATUS_ESCALATED = "escalated"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_PM_REVIEW, "PM Review"),
        (STATUS_ESCALATED, "Escalated"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]

    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="blocked_issues",
    )
    master_code = models.ForeignKey(
        MasterCode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )

    issue = models.TextField(blank=True, default="")
    reason = models.TextField(blank=True, default="")
    suggested_solution = models.TextField(blank=True, default="")
    impact = models.TextField(blank=True, default="")
    amended_solution = models.TextField(blank=True, default="")

    pm_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        blank=True,
    )

    priority = models.CharField(max_length=50, blank=True, default="")
    responsible_party = models.CharField(max_length=150, blank=True, default="")

    pm_note = models.TextField(blank=True, default="")

    follow_up_with = models.CharField(
        max_length=150,
        blank=True,
        default=""
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_blocked_issues",
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    escalated_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="escalated_blocked_issues",
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.issue[:80] if self.issue else "Blocked Issue"


class SiteVisit(models.Model):
    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="site_visits",
    )
    visit_code = models.ForeignKey(
        LookupItem,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        limit_choices_to={"list_type": "site_visit_code", "is_active": True},
        related_name="site_visit_code_entries",
    )
    visitor_name = models.CharField(max_length=150, blank=True, default="")
    visitor_entity = models.CharField(max_length=150, blank=True, default="")
    purpose = models.TextField(blank=True, default="")
    visit_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return self.visitor_name or "Site Visit"


class WorkerProfile(models.Model):
    SOURCE_COMPANY = "company"
    SOURCE_SUBCONTRACTOR = "subcontractor"
    SOURCE_WORKSHOP = "workshop"
    SOURCE_TEMPORARY = "temporary"
    SOURCE_SUPPLIER_TEAM = "supplier_team"

    SOURCE_CHOICES = [
        (SOURCE_COMPANY, "Company Direct"),
        (SOURCE_SUBCONTRACTOR, "Subcontractor"),
        (SOURCE_WORKSHOP, "Workshop"),
        (SOURCE_TEMPORARY, "Temporary Labor"),
        (SOURCE_SUPPLIER_TEAM, "Supplier Team"),
    ]

    SKILL_CERTIFIED = "certified"
    SKILL_SKILLED = "skilled"
    SKILL_HELPER = "helper"
    SKILL_SUPERVISOR = "supervisor"
    SKILL_OPERATOR = "operator"
    SKILL_TECHNICIAN = "technician"

    SKILL_CHOICES = [
        (SKILL_CERTIFIED, "Certified"),
        (SKILL_SKILLED, "Skilled Worker"),
        (SKILL_HELPER, "Helper"),
        (SKILL_SUPERVISOR, "Supervisor"),
        (SKILL_OPERATOR, "Operator"),
        (SKILL_TECHNICIAN, "Technician"),
    ]

    name = models.CharField(max_length=255)
    worker_source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default=SOURCE_COMPANY,
    )
    company_name = models.CharField(max_length=255, blank=True, default="")
    skill_level = models.CharField(
        max_length=50,
        choices=SKILL_CHOICES,
        blank=True,
        default="",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "worker_source", "company_name")

    def __str__(self):
        return self.name


class WorkforceEntry(models.Model):
    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="workforce_entries",
    )
    master_code = models.ForeignKey(
        MasterCode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    worker = models.ForeignKey(
        WorkerProfile,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="daily_entries",
    )

    worker_name = models.CharField(max_length=255, blank=True, default="")
    worker_source = models.CharField(
        max_length=50,
        choices=WorkerProfile.SOURCE_CHOICES,
        blank=True,
        default="",
    )
    company_name = models.CharField(max_length=255, blank=True, default="")
    skill_level = models.CharField(
        max_length=50,
        choices=WorkerProfile.SKILL_CHOICES,
        blank=True,
        default="",
    )

    normal_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["worker_name"]

    def save(self, *args, **kwargs):
        if self.worker:
            self.worker_name = self.worker.name
            self.worker_source = self.worker.worker_source
            self.company_name = self.worker.company_name
            self.skill_level = self.worker.skill_level
        elif self.worker_name:
            worker, created = WorkerProfile.objects.get_or_create(
                name=self.worker_name.strip(),
                worker_source=self.worker_source or WorkerProfile.SOURCE_COMPANY,
                company_name=self.company_name or "",
                defaults={
                    "skill_level": self.skill_level or "",
                    "is_active": True,
                },
            )
            self.worker = worker

        super().save(*args, **kwargs)

    def __str__(self):
        return self.worker_name or "Worker Entry"


class EquipmentUsage(models.Model):
    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="equipment_usages",
    )
    master_code = models.ForeignKey(
        MasterCode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    equipment = models.ForeignKey(
        EquipmentMaster,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(default=1)
    working_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    idle_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.equipment or 'Equipment'} - Qty {self.quantity}"


class MaterialReceipt(models.Model):
    daily_report = models.ForeignKey(
        DailyReport,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="material_receipts",
    )
    master_code = models.ForeignKey(
        MasterCode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    material_name = models.CharField(max_length=150, blank=True, default="")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, default="")
    supplier = models.CharField(max_length=150, blank=True, default="")
    delivery_note_number = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return self.material_name or "Material Receipt"


class WorkProgressAttachment(models.Model):
    work_progress = models.ForeignKey(
        WorkProgress,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/active_works/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class BlockedIssueAttachment(models.Model):
    blocked_issue = models.ForeignKey(
        BlockedIssue,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/blocked_issues/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class SiteVisitAttachment(models.Model):
    site_visit = models.ForeignKey(
        SiteVisit,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/site_visits/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class WorkforceAttachment(models.Model):
    workforce_entry = models.ForeignKey(
        WorkforceEntry,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/workforce/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class EquipmentAttachment(models.Model):
    equipment_usage = models.ForeignKey(
        EquipmentUsage,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/equipment/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class MaterialAttachment(models.Model):
    material_receipt = models.ForeignKey(
        MaterialReceipt,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/materials/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]


class DailyReportChangeLog(models.Model):
    report = models.ForeignKey(
        DailyReport,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    field_name = models.CharField(max_length=150)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Daily Report Change Log"
        verbose_name_plural = "Daily Report Change Logs"
        ordering = ["-edited_at"]

    def __str__(self):
        return f"{self.field_name} changed on {self.edited_at}"


class DailyReportAttachment(models.Model):
    SECTION_GENERAL = "general"
    SECTION_OTHER = "other"

    SECTION_CHOICES = [
        (SECTION_GENERAL, "General"),
        (SECTION_OTHER, "Other"),
    ]

    daily_report = models.ForeignKey(
        DailyReport,
        on_delete=models.CASCADE,
        related_name="general_attachments",
    )
    section = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES,
        default=SECTION_GENERAL,
    )
    document_type = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="daily_reports/general/")
    description = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.section} - {self.daily_report_id}"


class UserActivityLog(models.Model):
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_SUBMIT = "submit"
    ACTION_APPROVE = "approve"
    ACTION_RETURN = "return"
    ACTION_REJECT = "reject"
    ACTION_PRINT = "print"

    ACTION_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_SUBMIT, "Submit"),
        (ACTION_APPROVE, "Approve"),
        (ACTION_RETURN, "Return"),
        (ACTION_REJECT, "Reject"),
        (ACTION_PRINT, "Print"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
    )
    description = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
    )
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.action}"
