from django.conf import settings
from django.db import models


User = settings.AUTH_USER_MODEL


class ActivityLog(models.Model):
    """
    Immutable audit/activity record for actions performed within a company.

    Activity logs are system-generated and should not be created or
    modified directly through the API.
    """

    # ---------------------------------------------------------
    # Task actions
    # ---------------------------------------------------------

    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"

    # ---------------------------------------------------------
    # Project actions
    # ---------------------------------------------------------

    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_UPDATED = "PROJECT_UPDATED"
    PROJECT_DELETED = "PROJECT_DELETED"
    OWNERSHIP_TRANSFERRED = "OWNERSHIP_TRANSFERRED"

    # ---------------------------------------------------------
    # Membership actions
    # ---------------------------------------------------------

    MEMBERSHIP_CREATED = "MEMBERSHIP_CREATED"
    MEMBERSHIP_UPDATED = "MEMBERSHIP_UPDATED"
    ROLE_CHANGED = "ROLE_CHANGED"

    # ---------------------------------------------------------
    # Report / comment actions
    # ---------------------------------------------------------

    REPORT_SUBMITTED = "REPORT_SUBMITTED"
    REPORT_UPDATED = "REPORT_UPDATED"
    REPORT_DELETED = "REPORT_DELETED"

    COMMENT_ADDED = "COMMENT_ADDED"
    COMMENT_UPDATED = "COMMENT_UPDATED"
    COMMENT_DELETED = "COMMENT_DELETED"

    # ---------------------------------------------------------
    # Organization / employee actions
    # ---------------------------------------------------------

    EMPLOYEE_CREATED = "EMPLOYEE_CREATED"
    EMPLOYEE_UPDATED = "EMPLOYEE_UPDATED"
    EMPLOYEE_SUSPENDED = "EMPLOYEE_SUSPENDED"
    EMPLOYEE_ACTIVATED = "EMPLOYEE_ACTIVATED"
    EMPLOYEE_TERMINATED = "EMPLOYEE_TERMINATED"
    EMPLOYEE_TRANSFERRED = "EMPLOYEE_TRANSFERRED"

    DEPARTMENT_CREATED = "DEPARTMENT_CREATED"
    DEPARTMENT_UPDATED = "DEPARTMENT_UPDATED"
    DEPARTMENT_DELETED = "DEPARTMENT_DELETED"

    TEAM_CREATED = "TEAM_CREATED"
    TEAM_UPDATED = "TEAM_UPDATED"
    TEAM_DELETED = "TEAM_DELETED"

    POSITION_CREATED = "POSITION_CREATED"
    POSITION_UPDATED = "POSITION_UPDATED"
    POSITION_DELETED = "POSITION_DELETED"

    # ---------------------------------------------------------
    # System actions
    # ---------------------------------------------------------

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    SECURITY_EVENT = "SECURITY_EVENT"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    AI_INSIGHT_CREATED = "AI_INSIGHT_CREATED"

    ACTION_CHOICES = (
        (TASK_CREATED, "Task Created"),
        (TASK_UPDATED, "Task Updated"),
        (TASK_DELETED, "Task Deleted"),
        (TASK_ASSIGNED, "Task Assigned"),
        (STATUS_CHANGED, "Status Changed"),

        (PROJECT_CREATED, "Project Created"),
        (PROJECT_UPDATED, "Project Updated"),
        (PROJECT_DELETED, "Project Deleted"),
        (OWNERSHIP_TRANSFERRED, "Ownership Transferred"),

        (MEMBERSHIP_CREATED, "Membership Created"),
        (MEMBERSHIP_UPDATED, "Membership Updated"),
        (ROLE_CHANGED, "Role Changed"),

        (REPORT_SUBMITTED, "Report Submitted"),
        (REPORT_UPDATED, "Report Updated"),
        (REPORT_DELETED, "Report Deleted"),

        (COMMENT_ADDED, "Comment Added"),
        (COMMENT_UPDATED, "Comment Updated"),
        (COMMENT_DELETED, "Comment Deleted"),

        (EMPLOYEE_CREATED, "Employee Created"),
        (EMPLOYEE_UPDATED, "Employee Updated"),
        (EMPLOYEE_SUSPENDED, "Employee Suspended"),
        (EMPLOYEE_ACTIVATED, "Employee Activated"),
        (EMPLOYEE_TERMINATED, "Employee Terminated"),
        (EMPLOYEE_TRANSFERRED, "Employee Transferred"),

        (DEPARTMENT_CREATED, "Department Created"),
        (DEPARTMENT_UPDATED, "Department Updated"),
        (DEPARTMENT_DELETED, "Department Deleted"),

        (TEAM_CREATED, "Team Created"),
        (TEAM_UPDATED, "Team Updated"),
        (TEAM_DELETED, "Team Deleted"),

        (POSITION_CREATED, "Position Created"),
        (POSITION_UPDATED, "Position Updated"),
        (POSITION_DELETED, "Position Deleted"),

        (LOGIN, "Login"),
        (LOGOUT, "Logout"),
        (SECURITY_EVENT, "Security Event"),
        (SYSTEM_EVENT, "System Event"),
        (AI_INSIGHT_CREATED, "AI Insight Created"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    action = models.CharField(
        max_length=60,
        choices=ACTION_CHOICES,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["company", "-created_at"],
                name="activity_company_created_idx",
            ),
            models.Index(
                fields=["project", "-created_at"],
                name="activity_project_created_idx",
            ),
            models.Index(
                fields=["task", "-created_at"],
                name="activity_task_created_idx",
            ),
            models.Index(
                fields=["user", "-created_at"],
                name="activity_user_created_idx",
            ),
            models.Index(
                fields=["action", "-created_at"],
                name="activity_action_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.user_id} - {self.created_at}"