from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from core.roles import Roles
from security.services import create_audit_log
from users.utils import send_invitation_email

from .models import CompanyInvite


class CompanyInviteService:

    DEFAULT_EXPIRATION_DAYS = 3

    @classmethod
    @transaction.atomic
    def create_invite(
        cls,
        *,
        company,
        email,
        role,
        created_by,
        request=None,
        days_valid=None,
    ):
        if not company.is_active:
            raise ValidationError(
                "Cannot invite users to an inactive company."
            )

        email = email.lower().strip()

        # Prevent duplicate active invitations.
        existing = CompanyInvite.objects.filter(
            company=company,
            email__iexact=email,
            status="PENDING",
        ).first()

        if existing:
            if existing.expires_at > timezone.now():
                raise ValidationError(
                    "A pending invitation already exists for this email."
                )

            existing.status = "EXPIRED"
            existing.save(update_fields=["status"])

        # enforce 1–7 day range
        duration = days_valid if days_valid in range(1, 8) else None
        if duration:
            expires_at = timezone.now() + timedelta(days=duration)
        else:
            expires_at = timezone.now() + timedelta(days=cls.DEFAULT_EXPIRATION_DAYS)


        invite = CompanyInvite.objects.create(
            company=company,
            email=email,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
        )

        transaction.on_commit(
            lambda: send_invitation_email(
                CompanyInvite.objects.select_related(
                    "company",
                    "created_by",
                ).get(pk=invite.pk)
            )
        )

        if request:
            create_audit_log(
                user=created_by,
                request=request,
                action="CREATE",
                description=(
                    f"Company invitation created for {email} "
                    f"with role {role}."
                ),
                obj=invite,
            )

        return invite

    @classmethod
    @transaction.atomic
    def accept_invite(
        cls,
        *,
        invite,
        user,
        request=None,
    ):
        invite = (
            CompanyInvite.objects
            .select_for_update()
            .select_related("company")
            .get(pk=invite.pk)
        )

        if invite.status != "PENDING":
            raise ValidationError(
                "This invitation is no longer pending."
            )

        if invite.expires_at <= timezone.now():
            invite.status = "EXPIRED"
            invite.save(update_fields=["status"])

            raise ValidationError(
                "This invitation has expired."
            )

        if not invite.company.is_active:
            raise ValidationError(
                "This company is currently inactive."
            )

        if user.email.lower() != invite.email.lower():
            raise PermissionDenied(
                "This invitation was issued to a different email address."
            )

        if user.company_id and user.company_id != invite.company_id:
            raise ValidationError(
                "You already belong to another company."
            )

        user.company = invite.company

        # Only assign the invited role if the user is not already
        # a higher-privileged account.
        if user.role not in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        ):
            user.role = invite.role

        user.save(
            update_fields=[
                "company",
                "role",
            ]
        )

        invite.status = "ACCEPTED"
        invite.accepted_at = timezone.now()

        invite.save(
            update_fields=[
                "status",
                "accepted_at",
            ]
        )

        if request:
            create_audit_log(
                user=user,
                request=request,
                action="UPDATE",
                description=(
                    f"Invitation accepted for "
                    f"{invite.company.name}."
                ),
                obj=invite,
            )

        return invite

    @classmethod
    @transaction.atomic
    def revoke_invite(
        cls,
        *,
        invite,
        user,
        request=None,
    ):
        if invite.status != "PENDING":
            raise ValidationError(
                "Only pending invitations can be revoked."
            )

        invite.status = "REVOKED"

        invite.save(
            update_fields=["status"]
        )

        if request:
            create_audit_log(
                user=user,
                request=request,
                action="UPDATE",
                description=(
                    f"Invitation revoked for {invite.email}."
                ),
                obj=invite,
            )

        return invite