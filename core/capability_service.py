from core.capabilities import Capabilities
from core.roles import Roles


class CapabilityService:
    """Authoritative capability resolver.

    Platform control-plane identities never inherit tenant capabilities.
    Tenant identities never receive platform-only capabilities, even if a
    malformed database grant exists.
    """

    @staticmethod
    def _authenticated(user):
        return bool(user and getattr(user, "is_authenticated", False))

    @staticmethod
    def is_platform_identity(user):
        if not CapabilityService._authenticated(user):
            return False
        return bool(getattr(user, "is_superuser", False) or getattr(user, "role", None) == Roles.SUPERUSER)

    @staticmethod
    def is_tenant_identity(user):
        return (
            CapabilityService._authenticated(user)
            and not CapabilityService.is_platform_identity(user)
            and bool(getattr(user, "company_id", None))
        )

    @classmethod
    def _tenant_capabilities(cls, user, *, company_only=False):
        if not cls.is_tenant_identity(user):
            return set()

        from companies.invitation_access import awaiting_position
        if awaiting_position(user):
            return set()

        result = set()

        # Company Administrator is configuration authority, not automatic
        # confidential-data authority. The preset intentionally excludes
        # compensation, precise location, HR-confidential data, etc.
        if getattr(user, "role", None) == Roles.ADMIN:
            result.update(Capabilities.PRESETS["COMPANY_ADMINISTRATOR"])

        grants = getattr(user, "capability_grants", None)
        if grants is not None:
            result.update(
                grants.filter(
                    company_id=user.company_id,
                    is_active=True,
                ).values_list("capability", flat=True)
            )

        profile = getattr(user, "employee_profile", None)
        if profile and profile.status == "ACTIVE" and getattr(profile, "position_id", None) and profile.position.is_active and profile.position.company_id == user.company_id:
            result.update(
                profile.position.capability_grants.filter(
                    company_id=user.company_id,
                    is_active=True,
                ).values_list("capability", flat=True)
            )

        from core.position_scope import PositionScope
        result.update(PositionScope.capabilities(user, company_only=company_only))

        # Defense in depth against manipulated DB/API grants.
        return {
            capability
            for capability in result
            if capability in Capabilities.values()
            and capability not in Capabilities.PLATFORM_ONLY
        }

    @classmethod
    def has(cls, user, capability):
        if capability not in Capabilities.values() or not cls._authenticated(user):
            return False

        if cls.is_platform_identity(user):
            return capability in Capabilities.PLATFORM_ONLY

        if capability in Capabilities.PLATFORM_ONLY:
            return False

        return capability in cls._tenant_capabilities(user)

    @classmethod
    def has_company(cls, user, capability):
        return cls.is_tenant_identity(user) and capability in cls._tenant_capabilities(user, company_only=True)

    @classmethod
    def all_for(cls, user):
        if not cls._authenticated(user):
            return set()

        if cls.is_platform_identity(user):
            return set(Capabilities.PLATFORM_ONLY)

        return cls._tenant_capabilities(user)
