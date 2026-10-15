from dataclasses import dataclass

# Stable legacy codes remain available for existing clients and saved state.
SETUP_VERSION = 3
SETUP_STEPS = (
    ("company", "Company profile"),
    ("organization", "Headquarters and branches"),
    ("departments", "Departments and teams"),
    ("positions", "Positions and reporting lines"),
    ("permissions", "Position responsibilities and access"),
    ("forms", "Choose and adapt forms"),
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
