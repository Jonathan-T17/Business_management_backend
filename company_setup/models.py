from django.db import models


class CompanySetupState(models.Model):
    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="setup_state",
    )
    current_step = models.CharField(max_length=50, blank=True)
    skipped_steps = models.JSONField(default=list, blank=True)
    completed_steps = models.JSONField(default=list, blank=True)
    selected_template = models.CharField(max_length=50, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class BusinessSetupTemplate(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]


class RolePreset(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="role_presets",
    )
    code = models.SlugField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    capabilities = models.JSONField(default=list)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_company_role_preset_code",
            ),
        ]


class RequestTypeDefinition(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="request_type_definitions")
    code = models.SlugField(max_length=100)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    sensitive = models.BooleanField(default=False)
    amount_enabled = models.BooleanField(default=False)
    amount_required = models.BooleanField(default=False)
    quantity_enabled = models.BooleanField(default=False)
    quantity_required = models.BooleanField(default=False)
    needed_by_enabled = models.BooleanField(default=True)
    needed_by_required = models.BooleanField(default=False)
    attachments_allowed = models.BooleanField(default=True)
    attachments_required = models.BooleanField(default=False)
    workflow = models.ForeignKey("workflows.WorkflowDefinition", null=True, blank=True, on_delete=models.SET_NULL, related_name="request_type_definitions")
    form_template = models.ForeignKey("forms_engine.FormTemplate", null=True, blank=True, on_delete=models.SET_NULL, related_name="request_type_definitions")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_company_request_type_code")]


class FieldActivityTemplate(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="field_activity_templates")
    name = models.CharField(max_length=120)
    activity_type = models.CharField(max_length=30)
    require_arrival = models.BooleanField(default=True)
    require_completion = models.BooleanField(default=True)
    require_location = models.BooleanField(default=False)
    require_photo = models.BooleanField(default=False)
    require_signature = models.BooleanField(default=False)
    require_notes = models.BooleanField(default=False)
    form_template = models.ForeignKey("forms_engine.FormTemplate", null=True, blank=True, on_delete=models.SET_NULL, related_name="field_activity_templates")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_company_field_template_name")]


class ApprovalRoute(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="approval_routes")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    workflow = models.OneToOneField("workflows.WorkflowDefinition", on_delete=models.CASCADE, related_name="approval_route")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_company_approval_route_name")]


class ReportingProcess(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="reporting_processes")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    schedule = models.OneToOneField("reporting_schedules.ReportingSchedule", on_delete=models.CASCADE, related_name="reporting_process")
    approval_route = models.ForeignKey(ApprovalRoute, null=True, blank=True, on_delete=models.SET_NULL, related_name="reporting_processes")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company", "name"], name="unique_company_reporting_process_name")]


class OfficialRecordPolicy(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="official_record_policies")
    source_type = models.CharField(max_length=50)
    prefix = models.CharField(max_length=10)
    automatic_issue = models.BooleanField(default=False)
    trigger_status = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "source_type"], name="unique_company_record_policy_source")]


class NotificationPolicy(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="notification_policies")
    event_code = models.CharField(max_length=80)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    user_can_disable_email = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "event_code"], name="unique_company_notification_policy_event")]