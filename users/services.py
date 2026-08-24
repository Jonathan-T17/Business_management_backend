from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from security.services import create_audit_log
from subscriptions.models import Plan, Subscription
from companies.models import Company  
from core.roles import Roles        
from .models import User


class UserService:

    @staticmethod
    @transaction.atomic
    def register_invited_user(
        *,
        email,
        full_name,
        password,
        invite_token,
    ):
        from companies.models import CompanyInvite
        from companies.services import CompanyInviteService

        try:
            invite = (
                CompanyInvite.objects
                .select_related("company")
                .get(token=invite_token)
            )
        except CompanyInvite.DoesNotExist:
            raise ValidationError({"invite": "Invitation not found."})

        if not invite.is_valid:
            raise ValidationError({"invite": "Invitation is expired or no longer valid."})

        if email.lower().strip() != invite.email.lower():
            raise ValidationError({"email": "This email does not match the invitation."})

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "A user with this email already exists."})

        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            password=password,
            company=invite.company,
            role=invite.role,
            is_active=False,
            email_verified=False,
        )

        CompanyInviteService.accept_invite(invite=invite, user=user)
        return user

    @staticmethod
    @transaction.atomic
    def register_company_admin(
        *,
        email,
        full_name,
        password,
        company_name,
    ):
        # Create company
        try:
            company = Company.objects.create(name=company_name)
            create_audit_log(
                user=None,  # no user yet
                action="COMPANY",
                request=None,  # if you have request context, pass it
                description=f"Company created: {company.name}",
                status="SUCCESS"
            )
        except IntegrityError:
            raise ValidationError({"company_name": "This company name is already registered."})

        # Create admin user
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            password=password,
            company=company,
            role=Roles.ADMIN,
            is_active=False,
            email_verified=False,
        )
        create_audit_log(
            user=user,
            action="USER",
            request=None,
            description="Company admin registered",
            status="SUCCESS"
        )

        # Assign starter plan
        starter_plan = Plan.objects.filter(name="Starter").first()
        if not starter_plan:
            raise ValidationError({"plan": "Starter plan is not configured."})

        subscription = Subscription.objects.create(
            company=company,
            plan=starter_plan,
            is_active=True,
        )
        create_audit_log(
            user=user,
            action="SUBSCRIPTION",
            request=None,
            description=f"Subscription assigned: {starter_plan.name}",
            status="SUCCESS"
        )

        return user
