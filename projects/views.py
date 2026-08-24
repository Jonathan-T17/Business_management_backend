from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from notifications.services import CommunicationService, create_notification
from subscriptions.services import SubscriptionService

from core.roles import Roles

from security.viewsets import SecureModelViewSet

from .models import (
    Project,
    ProjectMembership,
)

from .serializers import (
    ProjectSerializer,
    ProjectMembershipSerializer,
)

from .permissions import (
    IsProjectMember,
    IsProjectManager,
    IsProjectOwner,
)

from .project_roles import ProjectRoles

from .services import ProjectService


# ============================================================
# Project ViewSet
# ============================================================

class ProjectViewSet(SecureModelViewSet):

    serializer_class = ProjectSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    audit_action = "PROJECT_UPDATED"

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):

        user = self.request.user

        if user.role == Roles.SUPERUSER:

            return Project.objects.select_related(
                "company",
                "created_by",
            ).prefetch_related(
                "branches",
                "memberships",
            )

        queryset = Project.objects.filter(
            company=user.company,
        ).select_related(
            "company",
            "created_by",
        ).prefetch_related(
            "branches",
            "memberships",
        )

        # ----------------------------------------------------
        # ADMIN
        # ----------------------------------------------------

        if user.role == Roles.ADMIN:
            return queryset

        # ----------------------------------------------------
        # MANAGER / EMPLOYEE
        #
        # Project visibility requires:
        #
        # 1. explicit project membership
        # OR
        # 2. project is available to their branch
        #
        # Company-wide projects are not automatically visible
        # to every employee. Membership remains the safest
        # collaboration boundary.
        # ----------------------------------------------------

        return queryset.filter(
            memberships__user=user,
        ).distinct()

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
        ):

            return [
                IsAuthenticated(),
            ]

        if self.action in (
            "create",
        ):

            return [
                IsAuthenticated(),
            ]

        if self.action in (
            "update",
            "partial_update",
            "members",
        ):

            return [
                IsAuthenticated(),
            ]

        if self.action in (
            "destroy",
        ):

            return [
                IsAuthenticated(),
            ]

        return [
            IsAuthenticated(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(
        self,
        serializer,
    ):

        user = self.request.user

        #Enforce subscription project limits
        if (user.role != Roles.SUPERUSER
            and not SubscriptionService.can_add_project( user.company)
            ): raise self.PermissionDenied("Your subscription limit has been reached.")
        
        if user.role not in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        ):
            raise PermissionDenied(
                "You do not have permission to create projects."
            )

        branches = serializer.validated_data.get(
            "branches",
            [],
        )

        project = ProjectService.create_project(
            user=user,
            company=user.company,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get(
                "description",
                "",
            ),
            branches=branches,
            request=self.request,
        )

        serializer.instance = project

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(
        self,
        serializer,
    ):

        project = self.get_object()

        self._check_project_manager(project)

        ProjectService.update_project(
            project=project,
            user=self.request.user,
            validated_data=dict(
                serializer.validated_data
            ),
        )

        serializer.instance = project

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    def perform_destroy(
        self,
        instance,
    ):

        self._check_project_owner(instance)

        ProjectService.delete_project(
            project=instance,
            user=self.request.user,
        )

    # --------------------------------------------------------
    # Project members
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["get"],
        url_path="members",
    )
    def members(
        self,
        request,
        pk=None,
    ):

        project = self.get_object()

        self._check_project_member(project)

        memberships = (
            ProjectMembership.objects
            .filter(project=project)
            .select_related(
                "user",
                "added_by",
                "project",
            )
        )

        serializer = ProjectMembershipSerializer(
            memberships,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # Project statistics
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["get"],
        url_path="summary",
    )
    def summary(
        self,
        request,
        pk=None,
    ):

        project = self.get_object()

        self._check_project_member(project)

        membership_count = (
            project.memberships.count()
        )

        branch_count = (
            project.branches.count()
        )

        return Response(
            {
                "id": project.id,
                "name": project.name,
                "is_active": project.is_active,
                "scope": (
                    "COMPANY_WIDE"
                    if branch_count == 0
                    else "BRANCH_SCOPED"
                ),
                "branch_count": branch_count,
                "member_count": membership_count,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Internal permission helpers
    # ========================================================

    def _check_project_member(
        self,
        project,
    ):

        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        exists = ProjectMembership.objects.filter(
            project=project,
            user=user,
        ).exists()

        if not exists:

            raise PermissionDenied(
                "You are not a member of this project."
            )

        return True

    def _check_project_manager(
        self,
        project,
    ):

        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        membership = (
            ProjectMembership.objects.filter(
                project=project,
                user=user,
            ).first()
        )

        if not membership:

            raise PermissionDenied(
                "You are not a member of this project."
            )

        if membership.role not in (
            ProjectRoles.OWNER.value,
            ProjectRoles.MANAGER.value,
        ):

            raise PermissionDenied(
                "You do not have project management permission."
            )

        return True

    def _check_project_owner(
        self,
        project,
    ):

        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        exists = ProjectMembership.objects.filter(
            project=project,
            user=user,
            role=ProjectRoles.OWNER.value,
        ).exists()

        if not exists:

            raise PermissionDenied(
                "Only the project owner can delete this project."
            )

        return True


# ============================================================
# Project Membership ViewSet
# ============================================================

class ProjectMembershipViewSet(
    SecureModelViewSet
):

    serializer_class = ProjectMembershipSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    audit_action = "MEMBERSHIP_UPDATED"

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):

        user = self.request.user

        queryset = (
            ProjectMembership.objects
            .select_related(
                "project",
                "project__company",
                "user",
                "added_by",
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            project__company=user.company,
        )

        if user.role == Roles.ADMIN:
            return queryset

        return queryset.filter(
            project__memberships__user=user,
        ).distinct()

    # --------------------------------------------------------
    # Create membership
    # --------------------------------------------------------

    def perform_create(
        self,
        serializer,
    ):
        user = self.request.user

        if not SubscriptionService.can_add_user(
            self.request.user.company
            ): raise self.PermissionDenied(
                "Your subscription user limit has been reached."
                )

        project = serializer.validated_data["project"]
        member = serializer.validated_data["user"]
        role = serializer.validated_data["role"]

        self._check_project_manager(project)

        current_membership = (
            ProjectMembership.objects.filter(
                project=project,
                user=self.request.user,
            ).first()
        )

        # ----------------------------------------------------
        # Managers can only create contributors.
        # ----------------------------------------------------

        if (
            current_membership
            and current_membership.role
            == ProjectRoles.MANAGER.value
            and role != ProjectRoles.CONTRIBUTOR.value
        ):

            raise PermissionDenied(
                "Managers may only add contributors."
            )

        membership = ProjectService.add_member(
            project=project,
            user=self.request.user,
            member=member,
            role=role,
            request=self.request,
        )

        serializer.instance = membership


        # Send membership notification + email
        CommunicationService.send(
            recipient=membership.user,
            company=membership.project.company,
            notification_type="MEMBERSHIP_CREATED",
            title="Added to project",
            message=f"You were added to '{membership.project.name}' as {membership.role}.",
            reference_id=str(membership.project.id),
            url=f"/projects/{membership.project.id}",
            send_email=True,
            email_subject=f"You've been added to {membership.project.name}",
            email_template="emails/project_update.html",
            email_context={
                "project": membership.project,
                "membership": membership,
                "action_url": f"{settings.FRONTEND_URL}/projects/{membership.project.id}",
            },
        )


        # Notify existing members (in-app only, no email)
        existing_memberships = (
            ProjectMembership.objects
            .filter(project=project)
            .exclude(user=membership.user)  # skip the new member
            .select_related("user")
        )
    
        for m in existing_memberships:
            create_notification(
                recipient=m.user,
                company=project.company,
                notification_type="MEMBERSHIP_CREATED",
                title="New member joined",
                message=f"{membership.user.get_full_name()} was added to '{project.name}' as {membership.role}.",
                reference_id=str(project.id),
            )
    
    # --------------------------------------------------------
    # Update membership
    # --------------------------------------------------------

    def perform_update(
        self,
        serializer,
    ):

        membership = self.get_object()

        self._check_project_manager(
            membership.project
        )

        new_role = serializer.validated_data.get(
            "role",
            membership.role,
        )

        current_membership = (
            ProjectMembership.objects.filter(
                project=membership.project,
                user=self.request.user,
            ).first()
        )

        # Managers cannot modify owners/managers.
        if (
            current_membership
            and current_membership.role
            == ProjectRoles.MANAGER.value
        ):

            if membership.role in (
                ProjectRoles.OWNER.value,
                ProjectRoles.MANAGER.value,
            ):

                raise PermissionDenied(
                    "Managers cannot modify owners "
                    "or other managers."
                )

            if new_role != ProjectRoles.CONTRIBUTOR.value:

                raise PermissionDenied(
                    "Managers may only assign "
                    "the contributor role."
                )

        ProjectService.update_member(
            membership=membership,
            role=new_role,
            user=self.request.user,
        )

        serializer.instance = membership

    # --------------------------------------------------------
    # Remove membership
    # --------------------------------------------------------

    def perform_destroy(
        self,
        instance,
    ):

        self._check_project_manager(
            instance.project
        )

        current_membership = (
            ProjectMembership.objects.filter(
                project=instance.project,
                user=self.request.user,
            ).first()
        )

        # Managers cannot remove owners/managers.
        if (
            current_membership
            and current_membership.role
            == ProjectRoles.MANAGER.value
            and instance.role in (
                ProjectRoles.OWNER.value,
                ProjectRoles.MANAGER.value,
            )
        ):

            raise PermissionDenied(
                "Managers cannot remove owners "
                "or other managers."
            )

        ProjectService.remove_member(
            membership=instance,
            user=self.request.user,
        )


        # Notify the removed member (email + in-app)
        CommunicationService.send(
            recipient=instance.user,
            company=instance.project.company,
            notification_type="MEMBERSHIP_REMOVED",
            title="Removed from project",
            message=f"You have been removed from '{instance.project.name}'.",
            reference_id=str(instance.project.id),
            url=f"/projects/{instance.project.id}",
            send_email=True,
            email_subject=f"You've been removed from {instance.project.name}",
            email_template="emails/project_update.html",
            email_context={
                "project": instance.project,
                "membership": instance,
                "action_url": f"{settings.FRONTEND_URL}/projects/{instance.project.id}",
            },
        )
    
        # Notify remaining members (in-app only, no email)
        remaining_memberships = (
            ProjectMembership.objects
            .filter(project=instance.project)
            .exclude(user=instance.user)  # skip the removed member
            .select_related("user")
        )
    
        for m in remaining_memberships:
            create_notification(
                recipient=m.user,
                company=instance.project.company,
                notification_type="MEMBERSHIP_REMOVED",
                title="Member removed",
                message=f"{instance.user.get_full_name()} was removed from '{instance.project.name}'.",
                reference_id=str(instance.project.id),
            )
    
    # ========================================================
    # Internal permission helper
    # ========================================================

    def _check_project_manager(
        self,
        project,
    ):

        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        membership = (
            ProjectMembership.objects.filter(
                project=project,
                user=user,
            ).first()
        )

        if not membership:

            raise PermissionDenied(
                "You are not a member of this project."
            )

        if membership.role not in (
            ProjectRoles.OWNER.value,
            ProjectRoles.MANAGER.value,
        ):

            raise PermissionDenied(
                "You do not have project management permission."
            )

        return True