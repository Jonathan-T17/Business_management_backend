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
    def is_platform_operator(cls, user):
        return bool(cls._authenticated(user) and getattr(user, "is_superuser", False)
                    and getattr(user, "is_staff", False) and getattr(user, "is_active", False)
                    and not getattr(user, "is_deleted", False)
                    and not getattr(user, "must_change_password", False))

    @classmethod
    def platform_capabilities(cls, user):
        if not cls.is_platform_operator(user):
            return set()
        duty = getattr(user, "platform_duty", "OWNER")
        if duty == "OWNER":
            return set(Capabilities.PLATFORM_ONLY)
        presets = {
            "SECURITY": {Capabilities.VIEW_PLATFORM_SECURITY, Capabilities.MANAGE_PLATFORM_SECURITY,
                         Capabilities.VIEW_PLATFORM_AUDIT, Capabilities.VIEW_PLATFORM_HEALTH},
            "SUPPORT": {Capabilities.PLATFORM_SUPPORT, Capabilities.VIEW_PLATFORM_SUPPORT,
                        Capabilities.MANAGE_PLATFORM_SUPPORT},
            "SUBSCRIPTIONS": {Capabilities.MANAGE_PLATFORM_SUBSCRIPTIONS},
            "AUDITOR": {Capabilities.VIEW_PLATFORM_AUDIT, Capabilities.VIEW_PLATFORM_HEALTH},
        }
        return presets.get(duty, set())

    @classmethod
    def _tenant_capabilities(cls, user, *, company_only=False):
        if not cls.is_tenant_identity(user):
            return set()

        from companies.invitation_access import awaiting_position
        if awaiting_position(user):
            return set()

        result = set()
        # Ordinary published company forms are a membership feature. This grants
        # no permission to read other employees' submissions or make decisions.
        if not company_only and user.is_active and user.company.is_active and not getattr(user, "is_deleted", False) and user.role in {Roles.ADMIN, Roles.MANAGER, Roles.EMPLOYEE}:
            result.add(Capabilities.USE_FORMS)

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

        from core.position_scope import PositionScope
        result.update(PositionScope.primary_capabilities(user, company_only=company_only))
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
            return capability in cls.platform_capabilities(user)

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
            return cls.platform_capabilities(user)

        return cls._tenant_capabilities(user)
