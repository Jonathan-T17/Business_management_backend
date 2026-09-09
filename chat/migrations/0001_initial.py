from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0003_company_email_footer_company_email_from_name_and_more"),
        ("organizations", "0002_initial"),
        ("projects", "0002_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("scope", models.CharField(choices=[("COMPANY", "Company"), ("BRANCH", "Branch"), ("DEPARTMENT", "Department"), ("TEAM", "Team"), ("PROJECT", "Project"), ("DIRECT", "Direct")], max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="companies.branch")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="companies.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_conversations", to=settings.AUTH_USER_MODEL)),
                ("department", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="organizations.department")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="projects.project")),
                ("team", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="conversations", to="organizations.team")),
            ],
            options={"ordering": ["-updated_at"], "indexes": [models.Index(fields=["company", "scope", "updated_at"], name="chat_conver_company_c1966f_idx")]},
        ),
        migrations.CreateModel(
            name="ConversationMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("last_read_at", models.DateTimeField(blank=True, null=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="chat.conversation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversation_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("conversation", "user"), name="unique_conversation_member")]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("body", models.TextField()),
                ("attachment_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.conversation")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sent_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"], "indexes": [models.Index(fields=["conversation", "created_at"], name="chat_messag_convers_3154fc_idx")]},
        ),
    ]