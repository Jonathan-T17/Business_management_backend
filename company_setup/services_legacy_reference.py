from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from documents.models import DocumentCategory
from organizations.models import Department, Position
from security.services import create_audit_log
from workflows.models import WorkflowDefinition, WorkflowStepDefinition
from forms_engine.models import FormField, FormTemplate
from reporting_schedules.models import ReportingSchedule

from .models import ApprovalRoute, ReportingProcess


class BusinessSetupTemplateService:
    @classmethod
    @transaction.atomic
    def apply(cls, *, company, template, selections, actor, request):
        configuration = template.configuration
        created = {"departments": 0, "positions": 0, "document_categories": 0}
        if selections.get("departments", True):
            for name in configuration.get("departments", []):
                _, was_created = Department.objects.get_or_create(company=company, branch=None, name=name, defaults={"created_by": actor})
                created["departments"] += was_created
        if selections.get("positions", True):
            for title in configuration.get("positions", []):
                _, was_created = Position.objects.get_or_create(company=company, title=title)
                created["positions"] += was_created
        if selections.get("document_categories", True):
            for name in configuration.get("document_categories", []):
                _, was_created = DocumentCategory.objects.get_or_create(company=company, name=name)
                created["document_categories"] += was_created
        create_audit_log(user=actor, company=company, request=request, action="CREATE", description=f"Applied {template.name} business setup template.", obj=company)
        return created


class ApprovalRouteService:
    @classmethod
    def validate_steps(cls, *, company, steps):
        if not steps:
            raise ValueError("At least one approval step is required.")
        valid_types = {value for value, _ in WorkflowStepDefinition.RECIPIENT_TYPES}
        for step in steps:
            recipient_type = step.get("recipient_type")
            if recipient_type not in valid_types:
                raise ValueError("An approval step has an invalid recipient type.")
            if recipient_type == "POSITION" and not Position.objects.filter(id=step.get("recipient_position"), company=company).exists():
                raise ValueError("A selected position does not belong to this company.")

    @classmethod
    @transaction.atomic
    def create(cls, *, company, data, actor, request):
        steps = data.pop("steps")
        cls.validate_steps(company=company, steps=steps)
        code = f"approval-{slugify(data['name'])}-{ApprovalRoute.objects.filter(company=company).count() + 1}"
        workflow = WorkflowDefinition.objects.create(company=company, name=data["name"], code=code, description=data.get("description", ""), target_type=data.get("target_type", "FORM_SUBMISSION"), created_by=actor)
        for order, step in enumerate(steps, start=1):
            WorkflowStepDefinition.objects.create(workflow=workflow, name=step.get("name") or f"Approval {order}", order=order, recipient_type=step["recipient_type"], recipient_user_id=step.get("recipient_user"), recipient_role=step.get("recipient_role", ""), recipient_position_id=step.get("recipient_position"), approval_mode=step.get("approval_mode", "ANY"), can_reject=step.get("can_reject", True), can_return=step.get("can_return", True), notify_in_app=step.get("notify_in_app", True), notify_email=step.get("notify_email", True))
        route = ApprovalRoute.objects.create(company=company, name=data["name"], description=data.get("description", ""), workflow=workflow)
        create_audit_log(user=actor, company=company, request=request, action="CREATE", description=f"Created approval route: {route.name}.", obj=route)
        return route

    @classmethod
    @transaction.atomic
    def update(cls, *, route, data, actor, request):
        steps = data.pop("steps", None)
        if steps is not None:
            cls.validate_steps(company=route.company, steps=steps)
            route.workflow.steps.all().delete()
            for order, step in enumerate(steps, start=1):
                WorkflowStepDefinition.objects.create(workflow=route.workflow, name=step.get("name") or f"Approval {order}", order=order, recipient_type=step["recipient_type"], recipient_user_id=step.get("recipient_user"), recipient_role=step.get("recipient_role", ""), recipient_position_id=step.get("recipient_position"), approval_mode=step.get("approval_mode", "ANY"), can_reject=step.get("can_reject", True), can_return=step.get("can_return", True), notify_in_app=step.get("notify_in_app", True), notify_email=step.get("notify_email", True))
        for field in ("name", "description", "is_active"):
            if field in data:
                setattr(route, field, data[field])
        route.save()
        route.workflow.name = route.name
        route.workflow.description = route.description
        route.workflow.save(update_fields=["name", "description", "updated_at"])
        create_audit_log(user=actor, company=route.company, request=request, action="UPDATE", description=f"Updated approval route: {route.name}.", obj=route)
        return route


class ReportingProcessService:
    @classmethod
    @transaction.atomic
    def create(cls, *, company, data, actor, request):
        submitters = data.get("submitters", {})
        schedule_data = data.get("schedule", {})
        target_type = submitters.get("type")
        target_field = f"target_{target_type.lower()}" if target_type else ""
        if target_type not in {value for value, _ in ReportingSchedule.TARGET_TYPES}:
            raise ValueError("A valid submitter type is required.")
        target_value = submitters.get(f"{target_type.lower()}_id") if target_type != "ROLE" else submitters.get("role")
        if not target_value:
            raise ValueError("A submitter must be selected.")
        code = f"report-{slugify(data['name'])}-{ReportingProcess.objects.filter(company=company).count() + 1}"
        template = FormTemplate.objects.create(company=company, name=data["name"], code=code, description=data.get("description", ""), category=data.get("category", "CUSTOM"), created_by=actor, lifecycle_status="DRAFT")
        for order, field in enumerate(data.get("fields", [])):
            FormField.objects.create(template=template, key=field["key"], label=field["label"], field_type=field["type"], required=field.get("required", False), help_text=field.get("help_text", ""), options=field.get("options", []), order=order)
        route = None
        if data.get("approval_route"):
            route = ApprovalRoute.objects.filter(id=data["approval_route"], company=company).first()
            if not route:
                raise ValueError("The selected approval route does not belong to this company.")
        elif data.get("approval_steps"):
            route = ApprovalRouteService.create(company=company, data={"name": f"{data['name']} approval", "description": data.get("description", ""), "steps": data["approval_steps"]}, actor=actor, request=request)
        if route:
            template.workflow = route.workflow
            template.save(update_fields=["workflow"])
        schedule_values = {"company": company, "name": data["name"], "description": data.get("description", ""), "template": template, "frequency": schedule_data.get("frequency", "DAILY"), "target_type": target_type, "start_date": schedule_data.get("start_date", timezone.localdate()), "due_time": schedule_data.get("due_time"), "weekday": schedule_data.get("weekday"), "day_of_month": schedule_data.get("day_of_month"), "created_by": actor}
        schedule_values[target_field] = target_value
        schedule = ReportingSchedule.objects.create(**schedule_values)
        process = ReportingProcess.objects.create(company=company, name=data["name"], description=data.get("description", ""), schedule=schedule, approval_route=route)
        create_audit_log(user=actor, company=company, request=request, action="CREATE", description=f"Created reporting process: {process.name}.", obj=process)
        return process

    @classmethod
    @transaction.atomic
    def update(cls, *, process, data, actor, request):
        template = process.schedule.template
        if "approval_steps" in data:
            if process.approval_route:
                route = ApprovalRouteService.update(route=process.approval_route, data={"steps": data["approval_steps"]}, actor=actor, request=request)
            else:
                route = ApprovalRouteService.create(company=process.company, data={"name": f"{process.name} approval", "steps": data["approval_steps"]}, actor=actor, request=request)
                process.approval_route = route
            template.workflow = route.workflow
            template.save(update_fields=["workflow"])
        if "fields" in data:
            fields = data["fields"]
            keys = [field["key"] for field in fields]
            if len(keys) != len(set(keys)):
                raise ValueError("Reporting field keys must be unique.")
            template.fields.all().delete()
            for order, field in enumerate(fields):
                FormField.objects.create(template=template, key=field["key"], label=field["label"], field_type=field["type"], required=field.get("required", False), help_text=field.get("help_text", ""), options=field.get("options", []), order=order)
            template.version += 1
            template.save(update_fields=["version"])
        schedule_data = data.get("schedule", {})
        if schedule_data:
            for field in ("frequency", "due_time", "weekday", "day_of_month", "start_date", "end_date", "allow_late_submission"):
                if field in schedule_data:
                    setattr(process.schedule, field, schedule_data[field])
            process.schedule.save()
        for field in ("name", "description", "is_active"):
            if field in data:
                setattr(process, field, data[field])
        process.schedule.name = process.name
        process.schedule.description = process.description
        process.schedule.is_active = process.is_active
        process.schedule.save(update_fields=["name", "description", "is_active", "updated_at"])
        process.save()
        create_audit_log(user=actor, company=process.company, request=request, action="UPDATE", description=f"Updated reporting process: {process.name}.", obj=process)
        return process