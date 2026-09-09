from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from core.roles import Roles

from .models import Conversation, ConversationMember, Message
from .permissions import IsConversationMember
from .serializers import ConversationSerializer, MessageSerializer


class ChatPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ChatPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Conversation.objects.select_related(
            "company", "created_by", "branch", "department", "team", "project",
        ).prefetch_related("memberships__user")
        if user.role == Roles.SUPERUSER:
            company_id = self.request.query_params.get("company")
            return queryset.filter(company_id=company_id) if company_id else queryset
        return queryset.filter(
            company_id=user.company_id,
            memberships__user=user,
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company_id:
            raise PermissionDenied("A company is required to create a conversation.")
        conversation = serializer.save(company_id=user.company_id, created_by=user)
        ConversationMember.objects.create(conversation=conversation, user=user)

    @action(detail=True, methods=["post"], url_path="members")
    def add_member(self, request, pk=None):
        conversation = self.get_object()
        if conversation.created_by_id != request.user.id and request.user.role not in (Roles.ADMIN, Roles.SUPERUSER):
            raise PermissionDenied("Only the conversation owner or company admin can manage members.")
        user = request.data.get("user")
        member = conversation.company.users.filter(id=user, is_active=True).first()
        if not member:
            return Response({"detail": "Active company user not found."}, status=status.HTTP_404_NOT_FOUND)
        ConversationMember.objects.get_or_create(conversation=conversation, user=member)
        return Response({"detail": "Member added."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        ConversationMember.objects.filter(
            conversation=conversation,
            user=request.user,
        ).update(last_read_at=timezone.now())
        return Response({"detail": "Conversation marked as read."})


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsConversationMember]
    pagination_class = ChatPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(
            conversation__memberships__user=user,
            deleted_at__isnull=True,
        ).select_related("sender", "conversation")
        conversation = self.request.query_params.get("conversation")
        search = self.request.query_params.get("search")
        if conversation:
            queryset = queryset.filter(conversation_id=conversation)
        if search:
            queryset = queryset.filter(body__icontains=search)
        return queryset.order_by("created_at")

    def perform_create(self, serializer):
        conversation_id = self.request.data.get("conversation")
        if not Conversation.objects.filter(
            id=conversation_id,
            memberships__user=self.request.user,
        ).exists():
            raise PermissionDenied("You are not a member of this conversation.")
        serializer.save(
            conversation_id=conversation_id,
            sender=self.request.user,
        )

    def perform_update(self, serializer):
        if serializer.instance.sender_id != self.request.user.id:
            raise PermissionDenied("Only the sender can edit a message.")
        serializer.save(edited_at=timezone.now())

    def perform_destroy(self, instance):
        if instance.sender_id != self.request.user.id and self.request.user.role not in (Roles.ADMIN, Roles.SUPERUSER):
            raise PermissionDenied("Only the sender or an administrator can delete a message.")
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])