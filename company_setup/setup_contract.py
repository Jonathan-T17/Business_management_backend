from dataclasses import dataclass

# Stable legacy codes remain available for existing clients and saved state.
SETUP_VERSION = 2
SETUP_STEPS = (
    ("company", "Company profile"),
    ("organization", "Locations"),
    ("departments", "Departments and teams"),
    ("positions", "Positions and reporting lines"),
    ("permissions", "Permissions and access"),
    ("forms", "Forms and processes"),
    ("employees", "People and invitations"),
    ("finish", "Review and activate"),
    ("template", "Business template"),
    ("reporting", "Reporting"), ("workflows", "Approvals"),
    ("operations", "Operations"), ("documents", "Documents and records"),
    ("notifications", "Notifications"), ("security", "Security"),
    ("subscription", "Subscription"),
)
REQUIRED_STEPS = {"company", "organization", "departments", "positions", "permissions", "forms", "employees", "finish"}
REVIEW_STEPS = {"organization", "departments", "positions", "permissions", "employees"}

from core.capabilities import Capabilities
SENSITIVE_CAPABILITIES = Capabilities.SENSITIVE

@dataclass(frozen=True)
class SetupAction:
    code: str
    allowed: bool
    reason: str = ""
