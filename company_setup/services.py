from copy import deepcopy
from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError

from security.services import create_audit_log
from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from documents.models import DocumentCategory
from organizations.models import Department, Position

from .models import CompanySetupState, RolePreset
from .capability_policy import SetupCapabilityPolicy
from .readiness import SetupReadinessService
from .setup_contract import SETUP_STEPS, REQUIRED_STEPS

class SetupStateService:
    @classmethod
    @transaction.atomic
    def state_for(cls, company):
        state, _ = CompanySetupState.objects.select_for_update().get_or_create(company=company)
        return state

    @classmethod
    @transaction.atomic
    def complete_step(cls, *, company, step, actor, request=None):
        valid = {code for code, _ in SETUP_STEPS}
        if step not in valid:
            raise ValidationError({"step": "Unknown setup step."})

        state = cls.state_for(company)
        completed = list(dict.fromkeys([*state.completed_steps, step]))
        state.completed_steps = completed

        order = [code for code, _ in SETUP_STEPS]
        next_step = next((code for code in order if code not in completed and code not in state.skipped_steps), "")
        state.current_step = next_step
        state.save(update_fields=["completed_steps", "current_step", "updated_at"])

        create_audit_log(
            user=actor, company=company, request=request, action="UPDATE",
            description=f"Company setup step completed: {step}.", obj=state,
        )
        return state

    @classmethod
    @transaction.atomic
    def skip_step(cls, *, company, step, actor, reason, request=None):
        if step in REQUIRED_STEPS:
            raise ValidationError({"step": "This setup step cannot be skipped."})
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError({"reason": "A reason is required."})
        state = cls.state_for(company)
        state.skipped_steps = list(dict.fromkeys([*state.skipped_steps, step]))
        state.save(update_fields=["skipped_steps", "updated_at"])
        create_audit_log(
            user=actor, company=company, request=request, action="UPDATE",
            description=f"Company setup step skipped: {step}.", obj=state,
            metadata={"reason": reason},
        )
        return state

    @classmethod
    @transaction.atomic
    def finish(cls, *, company, actor, request=None):
        readiness = SetupReadinessService.evaluate(company)
        if not readiness["ready"]:
            raise ValidationError({"setup": "Blocking setup checks must be resolved first.", "readiness": readiness})
        state = cls.state_for(company)
        state.onboarding_completed = True
        state.current_step = ""
        state.save(update_fields=["onboarding_completed", "current_step", "updated_at"])
        create_audit_log(
            user=actor, company=company, request=request, action="UPDATE",
            description="Company onboarding completed.", obj=state,
        )
        return state

class RolePresetService:
    @classmethod
    @transaction.atomic
    def save(cls, *, company, actor, data, instance=None, request=None):
        capabilities = SetupCapabilityPolicy.validate_preset(
            actor=actor, capabilities=data.get("capabilities", getattr(instance, "capabilities", []))
        )
        if instance:
            if instance.company_id != company.id or instance.is_system:
                raise PermissionDenied("This preset cannot be modified.")
            instance.name = data.get("name", instance.name)
            instance.description = data.get("description", instance.description)
            instance.capabilities = capabilities
            instance.is_active = data.get("is_active", instance.is_active)
            instance.save()
            preset = instance
        else:
            code = slugify(data.get("code") or data["name"])
            preset, _ = RolePreset.objects.update_or_create(
                company=company, code=code,
                defaults={
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "capabilities": capabilities,
                    "is_system": False,
                    "is_active": data.get("is_active", True),
                },
            )
        create_audit_log(
            user=actor, company=company, request=request, action="UPDATE",
            description=f"Role preset configured: {preset.name}.", obj=preset,
        )
        return preset

class IdempotentBusinessTemplateService:
    """
    Re-applying a template converges on the requested baseline. It does not
    create count-based duplicates and does not delete company customizations.
    """
    @classmethod
    @transaction.atomic
    def apply(cls, *, company, template, selections, actor, request=None):
        config = deepcopy(template.configuration or {})
        created = {"departments": 0, "positions": 0, "document_categories": 0}

        if selections.get("departments", True):
            for name in config.get("departments", []):
                _, was_created = Department.objects.get_or_create(
                    company=company, branch=None, name=name,
                    defaults={"created_by": actor},
                )
                created["departments"] += int(was_created)

        if selections.get("positions", True):
            for title in config.get("positions", []):
                _, was_created = Position.objects.get_or_create(company=company, title=title)
                created["positions"] += int(was_created)

        if selections.get("document_categories", True):
            for item in config.get("document_categories", []):
                if isinstance(item, str):
                    name, defaults = item, {}
                else:
                    name, defaults = item["name"], {
                        key: value for key, value in item.items() if key != "name"
                    }
                _, was_created = DocumentCategory.objects.get_or_create(
                    company=company, name=name, defaults=defaults
                )
                created["document_categories"] += int(was_created)

        state = SetupStateService.state_for(company)
        state.selected_template = template.code
        state.save(update_fields=["selected_template", "updated_at"])

        create_audit_log(
            user=actor, company=company, request=request, action="CREATE",
            description=f"Applied business setup template: {template.name}.", obj=company,
            metadata={"template_code": template.code, "created": created},
        )
        return created
