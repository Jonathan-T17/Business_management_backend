from rest_framework import serializers

from core.roles import Roles

from .models import (
    Company,
    Branch,
    CompanyInvite,
)

class CompanySerializer(serializers.ModelSerializer):

    def validate_logo(self, value):
        if value is None:
            return value
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError('Choose a logo smaller than 2 MB.')
        image = getattr(value, 'image', None)
        if image is None or image.format not in {'PNG', 'JPEG', 'WEBP'}:
            raise serializers.ValidationError('Choose a PNG, JPG or WebP image.')
        if image.width > 4096 or image.height > 4096:
            raise serializers.ValidationError('Choose an image no larger than 4096 × 4096 pixels.')
        return value
    
    class Meta:
        model = Company

        fields = (
            "id",
            "name",
            "official_name",
            "registration_number",
            "slug",
            "description",
            "logo",

            "website",
            "phone",
            "email",
            "address",
            "country",
            "timezone",
            "default_currency",
            "date_format",
            "week_starts_on",
            "setup_completed_at",
            "headquarters",

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
            "is_active",
            "slug",
            "created_at",
            "updated_at",
            "setup_completed_at",
            "headquarters",
        )

    def validate_timezone(self, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value.strip())
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError("Choose a valid timezone, for example Africa/Kigali.")
        return value.strip()

    def validate_country(self, value):
        value = value.strip().upper()
        if len(value) != 2 or not value.isascii() or not value.isalpha():
            raise serializers.ValidationError("Use a two-letter country code, for example RW.")
        return value

    def validate_default_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isascii() or not value.isalpha():
            raise serializers.ValidationError("Use a three-letter currency code, for example RWF.")
        return value

    def validate_official_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Official company name is required.")
        return value.strip()

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
    is_headquarters = serializers.SerializerMethodField()

    def get_is_headquarters(self, obj) -> bool:
        return obj.company.headquarters_id == obj.pk

    class Meta:
        model = Branch

        fields = (
            "id",
            "company",
            "name",
            "code",
            "location",
            "is_headquarters",
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
    employee_profile_id = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()

    def _accepted_profile(self, obj):
        if obj.status != "ACCEPTED":
            return None
        from organizations.models import EmployeeProfile
        return EmployeeProfile.objects.filter(
            company_id=obj.company_id, user__email__iexact=obj.email,
        ).select_related("position").first()

    def get_employee_profile_id(self, obj) -> int | None:
        profile = self._accepted_profile(obj)
        return profile.pk if profile else None

    def get_assignment_status(self, obj) -> str:
        from django.utils import timezone
        if obj.status == "PENDING" and obj.expires_at <= timezone.now():
            return "EXPIRED"
        if obj.status != "ACCEPTED":
            return obj.status
        if obj.role == "ADMIN":
            return "ADMINISTRATOR"
        profile = self._accepted_profile(obj)
        has_active_position = (
            profile and profile.status == "ACTIVE" and profile.position_id
            and profile.position.is_active
            and profile.position.company_id == obj.company_id
        )
        return "POSITION_ASSIGNED" if has_active_position else "AWAITING_POSITION"

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
            "position",
            "status",
            "token",
            "expires_at",
            "accepted_at",
            "created_by",
            "created_at",
            "days_valid",
            "employee_profile_id",
            "assignment_status",
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

    def validate_position(self, value):
        if value and (value.company_id != self.context["request"].user.company_id or not value.is_active):
            raise serializers.ValidationError("Choose an active position in your company.")
        return value

    def validate_email(self, value):
        return value.strip().lower()

    def validate_role(self, value):
        request = self.context.get("request")

        if not request:
            return value

        user = request.user

        if value == Roles.SUPERUSER:
            raise serializers.ValidationError(
                "Platform roles cannot be assigned through company invitations."
            )
        if value == Roles.ADMIN and user.role != Roles.ADMIN:
            raise serializers.ValidationError(
                "Only a Company Administrator may invite another Company Administrator."
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
