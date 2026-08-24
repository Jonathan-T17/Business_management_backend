from django.conf import settings
from django.db import models

from companies.models import Company, Branch

from .project_roles import ProjectRoles


User = settings.AUTH_USER_MODEL


# ============================================================
# Project
# ============================================================

class Project(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # Project scope
    #
    # Empty branches = company-wide project.
    # One or more branches = branch-scoped project.
    # --------------------------------------------------------

    branches = models.ManyToManyField(
        Branch,
        related_name="projects",
        blank=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_project_name_per_company",
            ),
        ]

        indexes = [
            models.Index(
                fields=["company", "is_active"],
            ),
            models.Index(
                fields=["company", "created_at"],
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_company_wide(self):
        """
        A project with no branch restrictions is company-wide.
        """
        return not self.branches.exists()


# ============================================================
# Project Membership
# ============================================================

class ProjectMembership(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=ProjectRoles.choices(),
        default=ProjectRoles.CONTRIBUTOR,
    )

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_project_memberships",
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["joined_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="unique_project_membership",
            ),
        ]

        indexes = [
            models.Index(
                fields=["project", "role"],
            ),
            models.Index(
                fields=["user", "role"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} → "
            f"{self.project} "
            f"({self.role})"
        )