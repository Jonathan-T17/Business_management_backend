from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from companies.models import Company
from users.models import User

from .models import Conversation, ConversationMember, Message
from .views import ConversationViewSet, MessageViewSet


class ChatIsolationTests(TestCase):

    def setUp(self):
        self.company = Company.objects.create(name="Chat Company")
        self.other_company = Company.objects.create(name="Other Company")
        self.user = User.objects.create_user(
            email="chat-user@example.com",
            full_name="Chat User",
            password="Strong-test-password-123!",
            role="EMPLOYEE",
            company=self.company,
            is_active=True,
        )
        self.other_user = User.objects.create_user(
            email="other-user@example.com",
            full_name="Other User",
            password="Strong-test-password-123!",
            role="EMPLOYEE",
            company=self.other_company,
            is_active=True,
        )
        self.conversation = Conversation.objects.create(
            company=self.company,
            name="Team chat",
            scope=Conversation.COMPANY,
            created_by=self.user,
        )
        ConversationMember.objects.create(
            conversation=self.conversation,
            user=self.user,
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            body="Hello",
        )

    def test_other_company_cannot_list_conversation(self):
        request = APIRequestFactory().get("/api/chat/conversations/")
        force_authenticate(request, user=self.other_user)
        response = ConversationViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_non_member_cannot_list_messages(self):
        request = APIRequestFactory().get(
            "/api/chat/messages/",
            {"conversation": str(self.conversation.id)},
        )
        force_authenticate(request, user=self.other_user)
        response = MessageViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_member_can_mark_conversation_read(self):
        request = APIRequestFactory().post("/api/chat/conversations/read/")
        force_authenticate(request, user=self.user)
        response = ConversationViewSet.as_view({"post": "mark_read"})(
            request,
            pk=str(self.conversation.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(
            ConversationMember.objects.get(
                conversation=self.conversation,
                user=self.user,
            ).last_read_at
        )