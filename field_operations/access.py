from core.capability_service import CapabilityService
from core.capabilities import Capabilities


class FieldAccessService:
    @staticmethod
    def can_view_precise_location(user):
        return CapabilityService.has(user, getattr(Capabilities, "VIEW_FIELD_LOCATION", "VIEW_FIELD_LOCATION"))

    @classmethod
    def redact_stop(cls, *, user, data):
        result = dict(data)
        if not cls.can_view_precise_location(user):
            result.pop("latitude", None)
            result.pop("longitude", None)
        return result
