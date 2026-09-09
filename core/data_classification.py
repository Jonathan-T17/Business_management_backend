from dataclasses import dataclass

class DataClassification:
    NORMAL = "NORMAL"
    PERSONAL = "PERSONAL"
    FINANCIAL = "FINANCIAL"
    HR_CONFIDENTIAL = "HR_CONFIDENTIAL"
    COMPENSATION = "COMPENSATION"
    PRECISE_LOCATION = "PRECISE_LOCATION"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    MANAGEMENT_CONFIDENTIAL = "MANAGEMENT_CONFIDENTIAL"

    VALUES = {
        NORMAL, PERSONAL, FINANCIAL, HR_CONFIDENTIAL, COMPENSATION,
        PRECISE_LOCATION, SECURITY_SENSITIVE, MANAGEMENT_CONFIDENTIAL,
    }

    SENSITIVE = VALUES - {NORMAL, PERSONAL}

    @classmethod
    def max_classification(cls, values):
        rank = {
            cls.NORMAL: 0,
            cls.PERSONAL: 1,
            cls.MANAGEMENT_CONFIDENTIAL: 2,
            cls.FINANCIAL: 3,
            cls.HR_CONFIDENTIAL: 4,
            cls.COMPENSATION: 5,
            cls.PRECISE_LOCATION: 6,
            cls.SECURITY_SENSITIVE: 7,
        }
        values = [v for v in values if v in rank]
        return max(values, key=lambda v: rank[v]) if values else cls.NORMAL


@dataclass(frozen=True)
class ClassifiedValue:
    value: object
    classification: str = DataClassification.NORMAL


@dataclass(frozen=True)
class ClassificationPolicy:
    code: str
    searchable: bool
    analytics_safe: bool
    platform_support_visible: bool
    notification_preview_safe: bool
    export_requires_sensitive_authority: bool


POLICIES = {
    DataClassification.NORMAL: ClassificationPolicy("NORMAL", True, True, True, True, False),
    DataClassification.PERSONAL: ClassificationPolicy("PERSONAL", True, False, False, False, False),
    DataClassification.FINANCIAL: ClassificationPolicy("FINANCIAL", False, False, False, False, True),
    DataClassification.HR_CONFIDENTIAL: ClassificationPolicy("HR_CONFIDENTIAL", False, False, False, False, True),
    DataClassification.COMPENSATION: ClassificationPolicy("COMPENSATION", False, False, False, False, True),
    DataClassification.PRECISE_LOCATION: ClassificationPolicy("PRECISE_LOCATION", False, False, False, False, True),
    DataClassification.SECURITY_SENSITIVE: ClassificationPolicy("SECURITY_SENSITIVE", False, False, False, False, True),
    DataClassification.MANAGEMENT_CONFIDENTIAL: ClassificationPolicy("MANAGEMENT_CONFIDENTIAL", False, False, False, False, True),
}


def policy_for(code):
    if code not in DataClassification.VALUES:
        code = DataClassification.NORMAL
    return POLICIES[code]
