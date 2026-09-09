from rest_framework.exceptions import PermissionDenied
from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from core.data_classification import DataClassification
from core.visibility import VisibilityService


class OfficialRecordAccessService:
    CLASSIFICATION_CAPABILITY = {
        DataClassification.FINANCIAL: "VIEW_FINANCIAL_REPORTS",
        DataClassification.HR_CONFIDENTIAL: "VIEW_HR_CONFIDENTIAL",
        DataClassification.COMPENSATION: "VIEW_COMPENSATION",
        DataClassification.PRECISE_LOCATION: "VIEW_FIELD_LOCATION",
        DataClassification.SECURITY_SENSITIVE: "VIEW_COMPANY_SECURITY",
        DataClassification.MANAGEMENT_CONFIDENTIAL: "VIEW_OFFICIAL_RECORDS",
    }

    @classmethod
    def can_view(cls, *, user, record):
        if not getattr(user, "company_id", None) or record.company_id != user.company_id:
            return False
        source = record.source_object
        if source and not VisibilityService.can_view_generic_object(user=user, obj=source):
            return False
        required = cls.CLASSIFICATION_CAPABILITY.get(getattr(record, "classification", DataClassification.NORMAL))
        return not required or CapabilityService.has(user, getattr(Capabilities, required, required))

    @classmethod
    def require_export(cls, *, user, record, purpose):
        if not cls.can_view(user=user, record=record):
            raise PermissionDenied("Record access denied.")
        if not CapabilityService.has(user, Capabilities.EXPORT_OFFICIAL_RECORDS):
            raise PermissionDenied("Record export denied.")
        if getattr(record, "classification", DataClassification.NORMAL) in DataClassification.SENSITIVE and not (purpose or "").strip():
            raise PermissionDenied("A purpose is required to export sensitive records.")
