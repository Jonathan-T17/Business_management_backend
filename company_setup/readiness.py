from dataclasses import dataclass
from companies.models import Branch
from organizations.models import Department, EmployeeProfile, Position
from .setup_contract import REVIEW_STEPS
from .models import CompanySetupState
from .models import (
    ApprovalRoute, NotificationPolicy, OfficialRecordPolicy,
    ReportingProcess, RequestTypeDefinition, RolePreset,
)

@dataclass(frozen=True)
class Check:
    code: str
    severity: str
    passed: bool
    message: str
    destination: str
    blocking: bool = False

class SetupReadinessService:
    """
    Server-derived readiness. Client-provided completed_steps never decides
    whether a company is operationally ready.
    """
    @classmethod
    def checks(cls, company):
        checks = []
        profile_fields = ("official_name", "country", "timezone", "default_currency")
        missing = [f for f in profile_fields if not str(getattr(company, f, "") or "").strip()]
        checks.append(Check(
            "COMPANY_PROFILE", "ERROR" if missing else "INFO", not missing,
            "Complete company profile." if missing else "Company profile complete.",
            "/settings/company-profile", blocking=bool(missing),
        ))

        branches = Branch.objects.filter(company=company, is_active=True).exists()
        checks.append(Check("ACTIVE_BRANCH", "WARNING", branches,
                            "Add an active headquarters or branch." if not branches else "Active branch configured.",
                            "/branches"))

        departments = Department.objects.filter(company=company, is_active=True).exists()
        checks.append(Check("ACTIVE_DEPARTMENT", "WARNING", departments,
                            "Add an active department." if not departments else "Department configured.",
                            "/departments"))

        positions = Position.objects.filter(company=company, is_active=True).exists()
        checks.append(Check("POSITIONS", "WARNING", positions,
                            "Create at least one position." if not positions else "Positions configured.",
                            "/employees/positions"))

        active_employees = EmployeeProfile.objects.filter(company=company, status="ACTIVE")
        without_position = active_employees.filter(position__isnull=True).count()
        checks.append(Check("EMPLOYEE_POSITIONS", "WARNING", without_position == 0,
                            f"{without_position} active employees have no position." if without_position else "Active employees have positions.",
                            "/employees"))

        presets = RolePreset.objects.filter(company=company, is_active=True).exists() or RolePreset.objects.filter(company__isnull=True, is_system=True, is_active=True).exists()
        checks.append(Check("ROLE_PRESETS", "ERROR" if not presets else "INFO", presets,
                            "Configure at least one safe role preset." if not presets else "Role presets available.",
                            "/settings/roles-permissions", blocking=not presets))

        from forms_engine.models import FormTemplate
        forms = FormTemplate.objects.filter(company=company, is_active=True, lifecycle_status="PUBLISHED").exists()
        checks.append(Check("PUBLISHED_FORM", "INFO" if forms else "ERROR", forms,
                            "Initial form ready." if forms else "Publish your first working form.",
                            "/settings/forms", blocking=not forms))
        state = CompanySetupState.objects.filter(company=company).first()
        reviewed = set(state.completed_steps if state else [])
        for step, label in (("organization", "locations"), ("departments", "departments and teams"), ("positions", "positions and reporting lines"),
                            ("permissions", "permissions and access"), ("employees", "people and invitations")):
            passed = "v2:" + step in reviewed or (step == "departments" and bool(state and state.onboarding_completed and "v2:organization" in reviewed))
            checks.append(Check("REVIEW_" + step.upper(), "INFO" if passed else "ERROR", passed,
                "Reviewed " + label + "." if passed else "Review and confirm " + label + ".",
                "/settings/onboarding?step=" + step, blocking=not passed))
        checks.append(Check("STRUCTURE_LOCATION", "INFO" if branches else "ERROR", branches,
            "Location configured." if branches else "Add your headquarters, main office or first site.", "/branches", blocking=not branches))
        checks.append(Check("STRUCTURE_POSITION", "INFO" if positions else "ERROR", positions,
            "Active positions configured." if positions else "Create at least one active position.", "/employees/positions", blocking=not positions))
        return checks

    @classmethod
    def evaluate(cls, company):
        checks = cls.checks(company)
        blocking = [c for c in checks if c.blocking and not c.passed]
        warnings = [c for c in checks if not c.passed and not c.blocking]
        passed = sum(1 for c in checks if c.passed)
        score = round((passed / len(checks)) * 100) if checks else 100
        return {
            "ready": not blocking,
            "score": score,
            "status": "READY" if not blocking else "BLOCKED",
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
            "checks": [c.__dict__ for c in checks],
            "issues": [
                {"code": c.code, "severity": c.severity, "message": c.message, "url": c.destination}
                for c in checks if not c.passed
            ],
        }

    @classmethod
    def configured_steps(cls, company):
        passed = {c.code for c in cls.checks(company) if c.passed}
        result = {"employees", "departments"}  # Review can explicitly defer invitations; acceptance never blocks setup.
        for code, step in {"COMPANY_PROFILE":"company", "STRUCTURE_LOCATION":"organization",
                           "STRUCTURE_POSITION":"positions", "ROLE_PRESETS":"permissions", "PUBLISHED_FORM":"forms"}.items():
            if code in passed:
                result.add(step)
        return result

    @classmethod
    def completed_steps(cls, company):
        configured = cls.configured_steps(company)
        state = CompanySetupState.objects.filter(company=company).first()
        reviewed = set(state.completed_steps if state else [])
        return {step for step in configured if step not in REVIEW_STEPS or "v2:" + step in reviewed or (step == "departments" and bool(state and state.onboarding_completed and "v2:organization" in reviewed))}
