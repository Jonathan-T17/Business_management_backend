from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Project, ProjectMembership
from .project_roles import ProjectRoles

from core.audit import ActivityAudit


class ProjectService:
    """
    Business logic for project management.

    Views should primarily deal with HTTP concerns.
    Project rules belong here.
    """

    # ========================================================
    # Project
    # ========================================================

    @staticmethod
    @transaction.atomic
    def create_project(
        *,
        user,
        company,
        name,
        description="",
        branches=None,
        request=None,
    ):

        if not name or not name.strip():
            raise ValidationError(
                {"name": "Project name is required."}
            )

        if Project.objects.filter(
            company=company,
            name__iexact=name.strip(),
        ).exists():
            raise ValidationError(
                {
                    "name":
                    "A project with this name already exists "
                    "in this company."
                }
            )

        project = Project.objects.create(
            company=company,
            name=name.strip(),
            description=description or "",
            created_by=user,
        )

        if branches:
            project.branches.set(branches)

        ProjectMembership.objects.create(
            project=project,
            user=user,
            role=ProjectRoles.OWNER.value,
            added_by=user,
        )

        ActivityAudit.log(
            user=user,
            company=company,
            project=project,
            action="PROJECT_CREATED",
            metadata={
                "object_type": "Project",
                "object_id": str(project.id),
                "name": project.name,
            },
        )

        return project

    # ========================================================
    # Update project
    # ========================================================

    @staticmethod
    @transaction.atomic
    def update_project(
        *,
        project,
        user,
        validated_data,
    ):

        branches = validated_data.pop(
            "branches",
            None,
        )

        for field, value in validated_data.items():
            setattr(project, field, value)

        project.save()

        if branches is not None:
            project.branches.set(branches)

        ActivityAudit.log(
            user=user,
            company=project.company,
            project=project,
            action="PROJECT_UPDATED",
            metadata={
                "object_type": "Project",
                "object_id": str(project.id),
                "name": project.name,
            },
        )

        return project

    # ========================================================
    # Delete project
    # ========================================================

    @staticmethod
    @transaction.atomic
    def delete_project(
        *,
        project,
        user,
    ):

        project_id = project.id
        company = project.company
        name = project.name

        ActivityAudit.log(
            user=user,
            company=company,
            project=project,
            action="PROJECT_DELETED",
            metadata={
                "object_type": "Project",
                "object_id": str(project_id),
                "name": name,
            },
        )

        project.delete()

    # ========================================================
    # Add member
    # ========================================================

    @staticmethod
    @transaction.atomic
    def add_member(
        *,
        project,
        user,
        member,
        role,
        request=None,
    ):

        if member.company_id != project.company_id:
            raise ValidationError(
                {
                    "user":
                    "User does not belong to this company."
                }
            )

        if role not in ProjectRoles.values():
            raise ValidationError(
                {
                    "role":
                    "Invalid project role."
                }
            )

        if ProjectMembership.objects.filter(
            project=project,
            user=member,
        ).exists():
            raise ValidationError(
                {
                    "user":
                    "User is already a member of this project."
                }
            )

        # ----------------------------------------------------
        # Branch restriction
        # ----------------------------------------------------

        if project.branches.exists():

            if not member.branch_id:
                raise ValidationError(
                    {
                        "user":
                        "User must belong to a project branch."
                    }
                )

            if not project.branches.filter(
                id=member.branch_id
            ).exists():

                raise ValidationError(
                    {
                        "user":
                        "User's branch is not assigned "
                        "to this project."
                    }
                )

        membership = ProjectMembership.objects.create(
            project=project,
            user=member,
            role=role,
            added_by=user,
        )

        ActivityAudit.log(
            user=user,
            company=project.company,
            project=project,
            action="MEMBERSHIP_CREATED",
            metadata={
                "object_type": "ProjectMembership",
                "object_id": str(membership.id),
                "user_id": str(member.id),
                "role": role,
            },
        )

        return membership

    # ========================================================
    # Update member role
    # ========================================================

    @staticmethod
    @transaction.atomic
    def update_member(
        *,
        membership,
        role,
        user,
    ):

        old_role = membership.role

        if role not in ProjectRoles.values():
            raise ValidationError(
                {"role": "Invalid project role."}
            )

        # Only one OWNER is permitted.
        if role == ProjectRoles.OWNER.value:

            if ProjectMembership.objects.filter(
                project=membership.project,
                role=ProjectRoles.OWNER.value,
            ).exclude(
                id=membership.id
            ).exists():

                raise ValidationError(
                    {
                        "role":
                        "A project can have only one owner."
                    }
                )

        membership.role = role
        membership.save(update_fields=["role"])

        ActivityAudit.log(
            user=user,
            company=membership.project.company,
            project=membership.project,
            action="MEMBERSHIP_UPDATED",
            metadata={
                "object_type": "ProjectMembership",
                "object_id": str(membership.id),
                "user_id": str(membership.user_id),
                "old_role": old_role,
                "new_role": role,
            },
        )

        return membership

    # ========================================================
    # Remove member
    # ========================================================

    @staticmethod
    @transaction.atomic
    def remove_member(
        *,
        membership,
        user,
    ):

        if membership.role == ProjectRoles.OWNER.value:

            raise ValidationError(
                {
                    "detail":
                    "The project owner cannot be removed. "
                    "Transfer ownership first."
                }
            )

        project = membership.project
        member = membership.user

        ActivityAudit.log(
            user=user,
            company=project.company,
            project=project,
            action="MEMBERSHIP_DELETED",
            metadata={
                "object_type": "ProjectMembership",
                "object_id": str(membership.id),
                "user_id": str(member.id),
                "role": membership.role,
            },
        )

        membership.delete()