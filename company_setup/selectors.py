from companies.models import Branch
from organizations.models import Department, EmployeeProfile


class SetupHealthService:
    @classmethod
    def evaluate(cls, company):
        issues = []
        missing_fields = [field for field in ("official_name", "country", "timezone", "default_currency") if not getattr(company, field)]
        if missing_fields:
            issues.append(cls.issue("COMPANY_PROFILE_INCOMPLETE", "WARNING", len(missing_fields), "Complete your company profile.", "/settings/company"))
        if not Branch.objects.filter(company=company, is_active=True).exists():
            issues.append(cls.issue("NO_ACTIVE_BRANCH", "WARNING", 1, "Add a headquarters or branch.", "/settings/organization"))
        if not Department.objects.filter(company=company, is_active=True).exists():
            issues.append(cls.issue("NO_ACTIVE_DEPARTMENT", "WARNING", 1, "Add at least one department.", "/settings/organization"))
        without_position = EmployeeProfile.objects.filter(company=company, status="ACTIVE", position__isnull=True).count()
        if without_position:
            issues.append(cls.issue("EMPLOYEES_WITHOUT_POSITION", "WARNING", without_position, f"{without_position} employees have no position.", "/settings/employees"))
        return {"score": max(0, 100 - len(issues) * 20), "status": "READY" if not issues else "NEEDS_ATTENTION", "issues": issues}

    @staticmethod
    def issue(code, severity, count, message, destination):
        return {"code": code, "severity": severity, "count": count, "message": message, "destination": destination}