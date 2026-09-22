from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.roles import Roles
from users.models import User

from notifications.services import CommunicationService

from .models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStepDefinition,
    WorkflowStepInstance,
    WorkflowStepRecipient,
    WorkflowActionLog,
)


class WorkflowService:

    WORKFLOW_DELEGATION_PERMISSIONS = {
        "REPORT": "APPROVE_REPORTS",
        "REQUEST": "APPROVE_REQUESTS",
        "FORM_SUBMISSION": "REVIEW_SUBMISSIONS",
    }

    @staticmethod
    def can_act_for_recipient(*, actor, recipient, permission):
        from core.position_scope import PositionScope
        if not PositionScope.recipient_current(recipient): return False
        if recipient.user_id == actor.id:
            return True

        from organizations.models import EmployeeDelegation

        delegations = EmployeeDelegation.objects.filter(
            company=actor.company,
            from_user_id=recipient.user_id,
            to_user=actor,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
            status__in=["SCHEDULED", "ACTIVE"],
        )

        return any(
            permission in delegation.permissions
            for delegation in delegations
        )

    @classmethod
    def _delegation_permission(cls, instance):
        return cls.WORKFLOW_DELEGATION_PERMISSIONS.get(
            instance.workflow.target_type
        )

    # ========================================================
    # Resolve Recipients
    # ========================================================

    @staticmethod
    def resolve_recipients(
        *,
        step,
        company,
        submitted_by,
        target,
    ):
        recipient_type = (
            step.recipient_type
        )

        queryset = User.objects.filter(
            company=company,
            is_active=True,
            is_deleted=False,
        )

        # -----------------------------------
        # Specific user
        # -----------------------------------

        if recipient_type == "USER":

            if (
                step.recipient_user
                and step.recipient_user.company_id
                == company.id
                and step.recipient_user.is_active
            ):
                return [
                    step.recipient_user
                ]

            return []

        # -----------------------------------
        # Role
        # -----------------------------------

        if recipient_type == "ROLE":

            return list(
                queryset.filter(
                    role=step.recipient_role
                )
            )

        # -----------------------------------
        # Position
        # -----------------------------------

        if recipient_type == "POSITION":
            from core.position_scope import PositionScope
            return list(PositionScope.position_users(company=company,position=step.recipient_position,
                branch_id=getattr(target,"branch_id",None)))

        # -----------------------------------
        # Company admins
        # -----------------------------------

        if recipient_type == "COMPANY_ADMIN":

            return list(
                queryset.filter(
                    role=Roles.ADMIN
                )
            )

        # -----------------------------------
        # Submitter EmployeeProfile
        # -----------------------------------

        profile = getattr(
            submitted_by,
            "employee_profile",
            None,
        )

        if not profile:
            return []

        # -----------------------------------
        # Direct manager
        # -----------------------------------

        if (
            recipient_type
            == "REPORTER_MANAGER"
        ):

            if (
                profile.manager
                and profile.manager.is_active
            ):
                return [
                    profile.manager
                ]

            return []

        # -----------------------------------
        # Branch manager
        # -----------------------------------

        if (
            recipient_type
            == "BRANCH_MANAGER"
        ):

            branch = (
                getattr(
                    target,
                    "branch",
                    None,
                )
                or profile.branch
            )

            if (
                branch
                and branch.manager
                and branch.manager.is_active
            ):
                return [
                    branch.manager
                ]

            return []

        # -----------------------------------
        # Department manager
        # -----------------------------------

        if (
            recipient_type
            == "DEPARTMENT_MANAGER"
        ):

            department = (
                profile.department
            )

            if (
                department
                and department.manager
                and department.manager.is_active
            ):
                return [
                    department.manager
                ]

            return []

        # -----------------------------------
        # Team leader
        # -----------------------------------

        if (
            recipient_type
            == "TEAM_LEADER"
        ):

            team = profile.team

            if (
                team
                and team.leader
                and team.leader.is_active
            ):
                return [
                    team.leader
                ]

            return []

        return []

    # ========================================================
    # Start Workflow
    # ========================================================

    @classmethod
    @transaction.atomic
    def start(
        cls,
        *,
        workflow,
        target,
        submitted_by,
        request=None,
    ):

        if not workflow.is_active:
            raise ValidationError(
                "Workflow is inactive."
            )

        target_company = getattr(
            target,
            "company",
            None,
        )

        if not target_company:
            raise ValidationError(
                "Workflow target must belong to a company."
            )

        if (
            workflow.company_id
            != target_company.id
        ):
            raise ValidationError(
                "Workflow belongs to another company."
            )

        if (
            submitted_by.role
            != Roles.SUPERUSER
            and submitted_by.company_id
            != target_company.id
        ):
            raise ValidationError(
                "You cannot submit data for another company."
            )

        content_type = (
            ContentType.objects
            .get_for_model(target)
        )

        # Prevent duplicate active workflow
        existing = (
            WorkflowInstance.objects
            .filter(
                company=target_company,
                content_type=content_type,
                object_id=str(target.pk),
                status="IN_PROGRESS",
            )
            .exists()
        )

        if existing:
            raise ValidationError(
                "This item already has an active workflow."
            )

        instance = (
            WorkflowInstance.objects.create(
                company=target_company,
                workflow=workflow,
                content_type=content_type,
                object_id=str(target.pk),
                submitted_by=
                    submitted_by,
            )
        )

        definitions = (
            workflow.steps
            .select_related(
                "recipient_user",
                "recipient_position",
            )
            .order_by("order")
        )

        if not definitions.exists():
            raise ValidationError(
                "Workflow has no steps."
            )

        runtime_steps = []

        for definition in definitions:

            runtime = (
                WorkflowStepInstance.objects.create(
                    workflow_instance=
                        instance,

                    definition_step=
                        definition,

                    order=
                        definition.order,

                    name=
                        definition.name,

                    approval_mode=
                        definition.approval_mode,

                    can_reject=
                        definition.can_reject,

                    can_return=
                        definition.can_return,

                    status="WAITING",
                )
            )

            recipients = (
                cls.resolve_recipients(
                    step=definition,
                    company=target_company,
                    submitted_by=
                        submitted_by,
                    target=target,
                )
            )

            if (
                definition.is_required
                and not recipients
            ):
                raise ValidationError(
                    f"No recipient could be "
                    f"resolved for workflow step "
                    f"'{definition.name}'."
                )

            for recipient in recipients:

                WorkflowStepRecipient.objects.create(
                    step=runtime,
                    user=recipient,
                )

            runtime_steps.append(
                runtime
            )

        first = runtime_steps[0]

        cls._activate_step(
            first
        )

        WorkflowActionLog.objects.create(
            workflow_instance=instance,
            actor=submitted_by,
            action="SUBMITTED",
        )

        cls._update_target_status(
            target,
            "SUBMITTED",
        )

        cls._notify_step(
            first,
            target,
        )

        return instance

    # ========================================================
    # Approve
    # ========================================================

    @classmethod
    @transaction.atomic
    def approve(
        cls,
        *,
        instance,
        user,
        note="",
    ):

        step = cls._current_step(
            instance
        )

        recipient = (
            cls._recipient_for_user(
                step,
                user,
                permission=cls._delegation_permission(instance),
            )
        )

        recipient.status = "APPROVED"
        recipient.acted_at = (
            timezone.now()
        )
        recipient.note = note

        recipient.save(
            update_fields=[
                "status",
                "acted_at",
                "note",
            ]
        )

        WorkflowActionLog.objects.create(
            workflow_instance=
                instance,
            step=step,
            actor=user,
            action="APPROVED",
            note=note,
            metadata={
                "acting_for_user_id": (
                    str(recipient.user_id)
                    if recipient.user_id != user.id
                    else None
                ),
                "delegated": recipient.user_id != user.id,
            },
        )

        complete = False

        if (
            step.approval_mode
            == "ANY"
        ):
            complete = True

            step.recipients.filter(
                status="PENDING"
            ).exclude(
                id=recipient.id
            ).update(
                status="SKIPPED"
            )

        else:
            complete = (
                not step.recipients
                .exclude(
                    status__in=[
                        "APPROVED",
                        "SKIPPED",
                    ]
                )
                .exists()
            )

        if complete:
            cls._complete_step(
                instance,
                step,
                actor=user,
            )

        return instance

    # ========================================================
    # Reject
    # ========================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        *,
        instance,
        user,
        note,
    ):

        step = cls._current_step(
            instance
        )

        if not step.can_reject:
            raise ValidationError(
                "This step cannot reject the item."
            )

        if not note.strip():
            raise ValidationError(
                "A rejection reason is required."
            )

        recipient = (
            cls._recipient_for_user(
                step,
                user,
                permission=cls._delegation_permission(instance),
            )
        )

        recipient.status = "REJECTED"
        recipient.acted_at = timezone.now()
        recipient.note = note

        recipient.save(
            update_fields=[
                "status",
                "acted_at",
                "note",
            ]
        )

        step.status = "REJECTED"
        step.completed_at = timezone.now()

        step.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        instance.status = "REJECTED"
        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        WorkflowActionLog.objects.create(
            workflow_instance=instance,
            step=step,
            actor=user,
            action="REJECTED",
            note=note,
            metadata={
                "acting_for_user_id": (
                    str(recipient.user_id)
                    if recipient.user_id != user.id
                    else None
                ),
                "delegated": recipient.user_id != user.id,
            },
        )

        cls._update_target_status(
            instance.content_object,
            "REJECTED",
        )

        return instance

    # ========================================================
    # Return for correction
    # ========================================================

    @classmethod
    @transaction.atomic
    def return_for_correction(
        cls,
        *,
        instance,
        user,
        note,
    ):

        step = cls._current_step(
            instance
        )

        if not step.can_return:
            raise ValidationError(
                "This step cannot return the item."
            )

        if not note.strip():
            raise ValidationError(
                "A return reason is required."
            )

        recipient = (
            cls._recipient_for_user(
                step,
                user,
                permission=cls._delegation_permission(instance),
            )
        )

        recipient.status = "RETURNED"
        recipient.acted_at = timezone.now()
        recipient.note = note

        recipient.save(
            update_fields=[
                "status",
                "acted_at",
                "note",
            ]
        )

        step.status = "RETURNED"
        step.completed_at = timezone.now()

        step.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        instance.status = "RETURNED"
        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        WorkflowActionLog.objects.create(
            workflow_instance=instance,
            step=step,
            actor=user,
            action="RETURNED",
            note=note,
            metadata={
                "acting_for_user_id": (
                    str(recipient.user_id)
                    if recipient.user_id != user.id
                    else None
                ),
                "delegated": recipient.user_id != user.id,
            },
        )

        cls._update_target_status(
            instance.content_object,
            "RETURNED",
        )

        return instance

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _current_step(instance):

        step = (
            instance.steps
            .filter(
                status="PENDING"
            )
            .order_by("order")
            .first()
        )

        if not step:
            raise ValidationError(
                "There is no pending workflow step."
            )

        return step

    @staticmethod
    def _recipient_for_user(
        step,
        user,
        permission=None,
    ):
        recipients = step.recipients.filter(status="PENDING")
        for recipient in recipients:
            if WorkflowService.can_act_for_recipient(
                actor=user,
                recipient=recipient,
                permission=permission,
            ):
                return recipient

        raise ValidationError(
            "You are not an active recipient for this workflow step."
        )

    @staticmethod
    def _activate_step(step):

        step.status = "PENDING"
        step.started_at = timezone.now()

        step.save(
            update_fields=[
                "status",
                "started_at",
            ]
        )

    @classmethod
    def _complete_step(
        cls,
        instance,
        step,
        actor=None,
    ):

        step.status = "APPROVED"
        step.completed_at = timezone.now()

        step.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        next_step = (
            instance.steps
            .filter(
                order__gt=step.order,
                status="WAITING",
            )
            .order_by("order")
            .first()
        )

        if next_step:

            cls._activate_step(
                next_step
            )

            cls._notify_step(
                next_step,
                instance.content_object,
            )

            return

        instance.status = "APPROVED"
        instance.completed_at = timezone.now()

        instance.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        cls._update_target_status(
            instance.content_object,
            "APPROVED",
            actor=actor,
        )

    @staticmethod
    def _update_target_status(
        target,
        status,
        actor=None,
    ):

        if not target:
            return

        if hasattr(target, "status"):

            target.status = status

            fields = ["status"]

            if (
                status == "SUBMITTED"
                and hasattr(
                    target,
                    "submitted_at",
                )
            ):
                target.submitted_at = (
                    timezone.now()
                )

                fields.append(
                    "submitted_at"
                )

            if (
                status == "APPROVED"
                and hasattr(
                    target,
                    "approved_at",
                )
            ):
                target.approved_at = (
                    timezone.now()
                )

                fields.append(
                    "approved_at"
                )

            target.save(
                update_fields=fields
            )

            if status == "APPROVED" and actor:
                record_type = {
                    "reports": "REPORT",
                    "forms_engine": "FORM_SUBMISSION",
                }.get(target._meta.app_label)
                if record_type:
                    from records_management.services import OfficialRecordService

                    OfficialRecordService.issue_if_configured(
                        source=target,
                        record_type=record_type,
                        status=status,
                        actor=actor,
                        title=getattr(target, "title", None) or str(target),
                        snapshot={
                            "status": status,
                            "source_id": str(target.pk),
                        },
                        branch=getattr(target, "branch", None),
                    )

    @staticmethod
    def _notify_step(
        step,
        target,
    ):

        definition = (
            step.definition_step
        )

        if not definition:
            return

        for assignment in (
            step.recipients
            .select_related("user")
            .all()
        ):

            recipient = (
                assignment.user
            )

            CommunicationService.send(
                recipient=recipient,

                company=
                    step.workflow_instance.company,

                notification_type=
                    "WORKFLOW_ACTION",

                title=(
                    f"Action required: "
                    f"{step.name}"
                ),

                message=(
                    "An item is waiting "
                    "for your review."
                ),

                reference_id=
                    str(
                        step.workflow_instance.id
                    ),

                send_email=
                    definition.notify_email,

                email_subject=(
                    f"Action required: "
                    f"{step.name}"
                ),

                email_template=(
                    "emails/"
                    "workflow_action.html"
                ),

                email_context={
                    "step": step,
                    "target": target,
                },
            )