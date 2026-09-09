from dataclasses import dataclass

SETUP_STEPS = (
    ("company", "Company Profile"),
    ("template", "Business Template"),
    ("organization", "Organization"),
    ("employees", "Employees"),
    ("permissions", "Roles and Permissions"),
    ("reporting", "Reporting"),
    ("workflows", "Approvals"),
    ("operations", "Operations"),
    ("documents", "Documents and Records"),
    ("notifications", "Notifications"),
    ("security", "Security"),
    ("subscription", "Subscription"),
    ("finish", "Finish"),
)

REQUIRED_STEPS = {
    "company",
    "organization",
    "permissions",
    "security",
    "subscription",
    "finish",
}

SENSITIVE_CAPABILITIES = {
    "VIEW_COMPENSATION",
    "MANAGE_COMPENSATION",
    "VIEW_COMPENSATION_HISTORY",
    "VIEW_HR_CONFIDENTIAL",
    "MANAGE_HR_CONFIDENTIAL",
    "VIEW_PRECISE_LOCATION",
    "EXPORT_SENSITIVE_DATA",
    "VIEW_COMPANY_SECURITY",
    "TERMINATE_COMPANY_SESSIONS",
}

@dataclass(frozen=True)
class SetupAction:
    code: str
    allowed: bool
    reason: str = ""
