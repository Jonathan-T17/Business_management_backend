from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from security.services import create_audit_log
from .models import SupportMessage, SupportTicket

SENSITIVE_CATEGORIES = {"SECURITY": "SECURITY", "BILLING": "BILLING"}
SAFE_CONTEXT_KEYS = {"application_version", "page", "module", "object_type", "object_id"}
ALLOWED_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "CLOSED"},
    "IN_PROGRESS": {"WAITING_FOR_CUSTOMER", "RESOLVED", "CLOSED"},
    "WAITING_FOR_CUSTOMER": {"IN_PROGRESS", "RESOLVED", "CLOSED"},
    "RESOLVED": {"IN_PROGRESS", "CLOSED"},
    "CLOSED": set(),
}

class SupportTicketService:
    @classmethod
    @transaction.atomic
    def create(cls, *, actor, category, subject, description, requested_priority="NORMAL", context=None, request=None):
        if not actor.company_id:
            raise PermissionDenied("A company account is required.")
        safe_context = {k: v for k, v in (context or {}).items() if k in SAFE_CONTEXT_KEYS}
        ticket = SupportTicket.objects.create(
            company=actor.company, created_by=actor, category=category,
            sensitivity=SENSITIVE_CATEGORIES.get(category, "NORMAL"),
            subject=subject, description=description, requested_priority=requested_priority,
            priority="HIGH" if category == "SECURITY" and requested_priority == "URGENT" else requested_priority,
            context={**safe_context, "company_id": str(actor.company_id), "user_id": str(actor.id)},
        )
        create_audit_log(user=actor, company=actor.company, request=request, action="SUPPORT_TICKET_CREATED", description=f"Support ticket {ticket.reference} created.", obj=ticket)
        return ticket

    @classmethod
    def can_view(cls, *, actor, ticket):
        if CapabilityService.has(actor, Capabilities.PLATFORM_SUPPORT):
            if ticket.sensitivity == "SECURITY":
                return CapabilityService.has(actor, Capabilities.VIEW_PLATFORM_SECURITY)
            return True
        if actor.company_id != ticket.company_id:
            return False
        if actor.id == ticket.created_by_id:
            return True
        if not CapabilityService.has(actor, Capabilities.VIEW_COMPANY_SUPPORT):
            return False
        if ticket.sensitivity in {"SECURITY", "BILLING", "RESTRICTED"}:
            return CapabilityService.has(actor, Capabilities.VIEW_SENSITIVE_SUPPORT)
        return True

    @classmethod
    @transaction.atomic
    def add_message(cls, *, ticket, actor, body, internal=False, request=None):
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        if not cls.can_view(actor=actor, ticket=ticket):
            raise PermissionDenied("You cannot access this support ticket.")
        platform_support = CapabilityService.has(actor, Capabilities.PLATFORM_SUPPORT)
        if internal and not platform_support:
            raise PermissionDenied("Internal notes are restricted to platform support.")
        if ticket.status == "CLOSED":
            raise ValidationError("Closed tickets do not accept replies.")
        if ticket.status == "RESOLVED" and not internal:
            ticket.status = "IN_PROGRESS"
            ticket.resolved_at = None
            ticket.save(update_fields=["status", "resolved_at", "updated_at"])
        message = SupportMessage.objects.create(ticket=ticket, author=actor, body=body, visibility="INTERNAL" if internal else "CUSTOMER")
        create_audit_log(user=actor, company=ticket.company, request=request, action="SUPPORT_MESSAGE_ADDED", description=f"Message added to support ticket {ticket.reference}.", obj=ticket, metadata={"visibility": message.visibility})
        return message

    @classmethod
    @transaction.atomic
    def transition(cls, *, ticket, actor, new_status, reason="", request=None):
        if not CapabilityService.has(actor, Capabilities.MANAGE_PLATFORM_SUPPORT):
            raise PermissionDenied("Platform support management authority is required.")
        ticket = SupportTicket.objects.select_for_update().get(pk=ticket.pk)
        if new_status not in ALLOWED_TRANSITIONS[ticket.status]:
            raise ValidationError(f"Cannot move support ticket from {ticket.status} to {new_status}.")
        ticket.status = new_status
        if new_status == "RESOLVED":
            ticket.resolved_at = timezone.now()
        elif new_status == "CLOSED":
            ticket.closed_at = timezone.now()
        else:
            ticket.resolved_at = None
        ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
        create_audit_log(user=actor, company=ticket.company, request=request, action="SUPPORT_STATUS_CHANGED", description=f"Support ticket {ticket.reference} status changed.", obj=ticket, metadata={"status": new_status, "reason": reason[:500]})
        return ticket
