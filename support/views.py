from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.authorization import Authorization
from core.roles import Roles
from notifications.services import create_notification
from security.services import create_audit_log
from users.models import User

from .models import SupportMessage, SupportTicket
from .permissions import CanUseSupport, IsPlatformSupport
from .serializers import (
    SupportMessageSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
    SupportTicketUpdateSerializer,
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, CanUseSupport)

    def get_queryset(self):
        queryset = SupportTicket.objects.select_related("company", "created_by", "assigned_to").prefetch_related("messages__author")
        if Authorization.is_platform_superuser(self.request.user):
            return queryset
        queryset = queryset.filter(company_id=self.request.user.company_id)
        if self.request.user.role != Roles.ADMIN:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return SupportTicketCreateSerializer
        if self.action in ("partial_update", "update"):
            return SupportTicketUpdateSerializer
        return SupportTicketSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise PermissionDenied("A company account is required to create a support ticket.")

        submitted_context = serializer.validated_data.get("context") or {}
        allowed_context = {
            key: submitted_context[key]
            for key in ("application_version", "page", "module", "object_type", "object_id")
            if key in submitted_context
        }
        ticket = serializer.save(
            company=user.company,
            created_by=user,
            context={
                **allowed_context,
                "company_id": str(user.company_id),
                "user_id": str(user.id),
                "user_role": user.role,
                "created_at": timezone.now().isoformat(),
            },
        )
        create_audit_log(user=user, company=user.company, request=self.request, action="CREATE", description=f"Support ticket created: {ticket.reference}.", obj=ticket)
        for platform_user in User.objects.filter(is_active=True).filter(role=Roles.SUPERUSER):
            create_notification(
                recipient=platform_user,
                title=f"New support ticket {ticket.reference}",
                message=ticket.subject,
                notification_type="SYSTEM",
                company=ticket.company,
                reference_id=str(ticket.id),
                url=f"/support/tickets/{ticket.id}",
            )

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        return self._create_reply(request, ticket)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "GET":
            return Response(SupportMessageSerializer(ticket.messages.all(), many=True).data)
        return self._create_reply(request, ticket)

    def _create_reply(self, request, ticket):
        if ticket.status in ("RESOLVED", "CLOSED") and not Authorization.is_platform_superuser(request.user):
            raise PermissionDenied("This ticket is no longer accepting replies.")
        serializer = SupportMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(ticket=ticket, author=request.user)
        if Authorization.is_platform_superuser(request.user):
            create_notification(
                recipient=ticket.created_by,
                title=f"SmartBiz Support replied to {ticket.reference}",
                message=message.body[:240],
                notification_type="SYSTEM",
                company=ticket.company,
                reference_id=str(ticket.id),
                url=f"/support/tickets/{ticket.id}",
            )
        else:
            for platform_user in User.objects.filter(is_active=True).filter(role=Roles.SUPERUSER):
                create_notification(
                    recipient=platform_user,
                    title=f"Customer replied to {ticket.reference}",
                    message=message.body[:240],
                    notification_type="SYSTEM",
                    company=ticket.company,
                    reference_id=str(ticket.id),
                    url=f"/platform/support/tickets/{ticket.id}",
                )
        create_audit_log(user=request.user, company=ticket.company, request=request, action="CREATE", description=f"Reply added to support ticket {ticket.reference}.", obj=ticket)
        return Response(SupportMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if not Authorization.is_platform_superuser(self.request.user):
            raise PermissionDenied("Only platform support staff may update ticket status or assignment.")
        ticket = serializer.save()
        if ticket.status in ("RESOLVED", "CLOSED") and not ticket.resolved_at:
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=("resolved_at", "updated_at"))
        create_audit_log(user=self.request.user, company=ticket.company, request=self.request, action="UPDATE", description=f"Support ticket {ticket.reference} updated.", obj=ticket)


class PlatformSupportTicketViewSet(SupportTicketViewSet):
    permission_classes = (IsAuthenticated, IsPlatformSupport)

    def get_queryset(self):
        return SupportTicket.objects.select_related(
            "company", "created_by", "assigned_to"
        ).prefetch_related("messages__author")
