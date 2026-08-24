from rest_framework import serializers

from core.roles import Roles

from .models import (
    Company,
    Branch,
    CompanyInvite,
)

class CompanySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Company

        fields = (
            "id",
            "name",
            "slug",
            "description",
            "logo",

            "website",
            "phone",
            "email",
            "address",

            "email_from_name",
            "email_reply_to",
            "email_footer",
            "email_notifications_enabled",

            "is_active",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Company name cannot be empty."
            )

        queryset = Company.objects.filter(
            name__iexact=value
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A company with this name already exists."
            )

        return value


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch

        fields = (
            "id",
            "company",
            "name",
            "code",
            "location",
            "manager",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Branch name cannot be empty."
            )

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return value

        company = getattr(
            request.user,
            "company",
            None,
        )

        if not company:
            return value

        queryset = Branch.objects.filter(
            company=company,
            name__iexact=value,
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise serializers.ValidationError(
                "A branch with this name already exists."
            )

        return value

    def validate_manager(self, manager):
        if manager is None:
            return manager

        request = self.context.get("request")

        if not request:
            return manager

        user = request.user
        company = getattr(user, "company", None)

        if company and manager.company_id != company.id:
            raise serializers.ValidationError(
                "Branch manager must belong to your company."
            )

        if not getattr(manager, "is_active", True):
            raise serializers.ValidationError(
                "Branch manager must be an active user."
            )

        if manager.role not in (
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.SUPERUSER,
        ):
            raise serializers.ValidationError(
                "The selected user cannot manage a branch."
            )

        return manager


class CompanyInviteSerializer(serializers.ModelSerializer):
    days_valid = serializers.ChoiceField(
        choices=[(i, f"{i} day{'s' if i > 1 else ''}") for i in range(1, 8)],
        write_only=True,
        required=False,
        help_text="Number of days (1–7) before the invite expires."
    )
    class Meta:
        model = CompanyInvite

        fields = (
            "id",
            "company",
            "email",
            "role",
            "status",
            "token",
            "expires_at",
            "accepted_at",
            "created_by",
            "created_at",
            "days_valid",
        )

        read_only_fields = (
            "id",
            "company",
            "status",
            "token",
            "expires_at",
            "accepted_at",
            "created_by",
            "created_at",
        )

    def validate_email(self, value):
        return value.strip().lower()

    def validate_role(self, value):
        request = self.context.get("request")

        if not request:
            return value

        user = request.user

        # Company admins cannot create another company admin
        # through the normal invitation workflow.
        if (
            user.role == Roles.ADMIN
            and value in (
                Roles.SUPERUSER,
                Roles.ADMIN,
            )
        ):
            raise serializers.ValidationError(
                "Company administrators may only invite managers or employees."
            )

        return value

    def validate(self, attrs):
        request = self.context.get("request")

        if not request:
            return attrs

        user = request.user
        company = getattr(user, "company", None)

        if not company:
            raise serializers.ValidationError(
                "You are not associated with a company."
            )

        email = attrs["email"]

        from users.models import User

        existing_user = User.objects.filter(
            email__iexact=email
        ).first()

        if existing_user and existing_user.company_id:
            if existing_user.company_id != company.id:
                raise serializers.ValidationError(
                    {
                        "email": (
                            "This email already belongs to another company."
                        )
                    }
                )

            raise serializers.ValidationError(
                {
                    "email": (
                        "This user is already a member of this company."
                    )
                }
            )

        return attrs






class PublicInviteSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = CompanyInvite

        fields = (
            "email",
            "role",
            "status",
            "company_name",
            "expires_at",
        )