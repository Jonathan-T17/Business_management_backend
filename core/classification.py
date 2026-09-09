from dataclasses import dataclass
from enum import StrEnum
class DataClassification(StrEnum):
    NORMAL='NORMAL'; PERSONAL='PERSONAL'; FINANCIAL='FINANCIAL'; HR_CONFIDENTIAL='HR_CONFIDENTIAL'; COMPENSATION='COMPENSATION'; PRECISE_LOCATION='PRECISE_LOCATION'; SECURITY_SENSITIVE='SECURITY_SENSITIVE'; MANAGEMENT_CONFIDENTIAL='MANAGEMENT_CONFIDENTIAL'
class DisclosureMode(StrEnum): FULL='FULL'; REDACTED='REDACTED'; HIDDEN='HIDDEN'
@dataclass(frozen=True)
class ClassificationRule:
    code: DataClassification; capability: str|None; searchable: bool; ai_allowed: bool; notification_preview: bool; export_requires_reason: bool; platform_default_access: bool; support_default_access: bool
RULES={
 DataClassification.NORMAL:ClassificationRule(DataClassification.NORMAL,None,True,True,True,False,False,False),
 DataClassification.PERSONAL:ClassificationRule(DataClassification.PERSONAL,'VIEW_PERSONAL_DATA',False,False,False,True,False,False),
 DataClassification.FINANCIAL:ClassificationRule(DataClassification.FINANCIAL,'VIEW_FINANCIAL_DATA',False,False,False,True,False,False),
 DataClassification.HR_CONFIDENTIAL:ClassificationRule(DataClassification.HR_CONFIDENTIAL,'VIEW_HR_CONFIDENTIAL',False,False,False,True,False,False),
 DataClassification.COMPENSATION:ClassificationRule(DataClassification.COMPENSATION,'VIEW_COMPENSATION',False,False,False,True,False,False),
 DataClassification.PRECISE_LOCATION:ClassificationRule(DataClassification.PRECISE_LOCATION,'VIEW_FIELD_LOCATION',False,False,False,True,False,False),
 DataClassification.SECURITY_SENSITIVE:ClassificationRule(DataClassification.SECURITY_SENSITIVE,'VIEW_COMPANY_SECURITY',False,False,False,True,False,False),
 DataClassification.MANAGEMENT_CONFIDENTIAL:ClassificationRule(DataClassification.MANAGEMENT_CONFIDENTIAL,'VIEW_MANAGEMENT_CONFIDENTIAL',False,False,False,True,False,False),
}
SEVERITY={DataClassification.NORMAL:0,DataClassification.PERSONAL:10,DataClassification.MANAGEMENT_CONFIDENTIAL:20,DataClassification.FINANCIAL:30,DataClassification.HR_CONFIDENTIAL:40,DataClassification.COMPENSATION:50,DataClassification.PRECISE_LOCATION:50,DataClassification.SECURITY_SENSITIVE:60}
def normalize(value):
    try:return value if isinstance(value,DataClassification) else DataClassification(str(value or 'NORMAL').upper())
    except ValueError:return DataClassification.NORMAL
def max_classification(*values):
    n=[normalize(v) for v in values]; return max(n,key=lambda v:SEVERITY[v],default=DataClassification.NORMAL)
