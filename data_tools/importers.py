import csv
import io
from itertools import islice
from datetime import timedelta

from rest_framework.exceptions import ValidationError, PermissionDenied
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone



class EmployeeImportService:
    REQUIRED_COLUMNS = {"email", "first_name", "last_name", "employee_id"}
    MAX_ROWS = 2000

    @classmethod
    def validate_rows(cls, *, company, rows):
        from organizations.models import EmployeeProfile

        errors = []
        valid = []
        seen_emails = set()
        seen_ids = set()
        from users.models import User
        from companies.models import CompanyInvite
        existing_emails = {email.lower() for email in User.objects.values_list("email", flat=True)}
        existing_emails.update(email.lower() for email in CompanyInvite.objects.filter(
            company=company, status="PENDING").values_list("email", flat=True))
        existing_ids = set(EmployeeProfile.objects.values_list("employee_id", flat=True))
        for index, row in enumerate(rows, start=2):
            row = {str(key).strip(): "" if value is None else str(value).strip() for key, value in row.items()}
            email = str(row.get("email", "")).strip().lower()
            employee_id = str(row.get("employee_id", "")).strip()
            row_errors = []
            unknown = set(row) - (cls.REQUIRED_COLUMNS | {"employment_type"})
            if unknown:
                row_errors.append({"field":"columns", "message":"Only email, first_name, last_name, employee_id and employment_type columns are allowed."})
            try:
                validate_email(email)
            except DjangoValidationError:
                row_errors.append({"field":"email", "message":"Enter a valid email address."})
            for field in ("email", "employee_id", "first_name", "last_name"):
                if not str(row.get(field, "")).strip():
                    row_errors.append({"field": field, "message": f"{field.replace('_', ' ').title()} is required."})
            if len(email) > 254 or len(employee_id) > 50 or len(row.get("first_name", "") + " " + row.get("last_name", "")) > 255:
                row_errors.append({"field":"row", "message":"An email, name or employee ID exceeds its maximum length."})
            if row.get("employment_type", "FULL_TIME") not in dict(EmployeeProfile.EMPLOYMENT_TYPES):
                row_errors.append({"field":"employment_type", "message":"Choose FULL_TIME, PART_TIME, CONTRACT or INTERN."})
            if email in existing_emails or email in seen_emails:
                row_errors.append({"field": "email", "message": "Email already exists."})
            if employee_id in existing_ids or employee_id in seen_ids:
                row_errors.append({"field": "employee_id", "message": "Employee ID already exists."})
            if row_errors:
                errors.append({"row": index, "errors": row_errors})
            else:
                row["email"] = email
                valid.append(row)
                seen_emails.add(email)
                seen_ids.add(employee_id)
        return {"valid_rows": valid, "errors": errors}

    @classmethod
    def rows_from_file(cls, file):
        file.open('rb')
        if file.name.lower().endswith(".xlsx"):
            from openpyxl import load_workbook

            workbook = load_workbook(file, read_only=True, data_only=True)
            rows = list(islice(workbook.active.values, cls.MAX_ROWS + 2))
            workbook.close()
            if not rows:
                return []
            headers = [
                str(value).strip() if value is not None else ""
                for value in rows[0]
            ]
            return [dict(zip(headers, row)) for row in rows[1:]]
        if file.name.lower().endswith(".csv"):
            return list(islice(csv.DictReader(io.StringIO(file.read().decode("utf-8-sig"))), cls.MAX_ROWS + 1))
        raise ValidationError("Only CSV and XLSX imports are supported.")

    @classmethod
    def validate_job(cls, *, job):
        rows = cls.rows_from_file(job.file)
        if len(rows) > cls.MAX_ROWS:
            raise ValidationError("Employee imports are limited to 2,000 rows.")
        result = cls.validate_rows(company=job.company, rows=rows)
        job.status = "READY"
        job.total_rows = len(rows)
        job.valid_rows = len(result["valid_rows"])
        job.invalid_rows = len(result["errors"])
        job.validation_result = result
        job.save(update_fields=["status", "total_rows", "valid_rows", "invalid_rows", "validation_result"])
        return result

    @classmethod
    @transaction.atomic
    def commit(cls, *, job, actor, request=None):
        from companies.models import CompanyInvite
        from organizations.services import EmployeeService
        from users.models import User

        from core.capabilities import Capabilities
        from core.capability_service import CapabilityService
        from subscriptions.services import SubscriptionService
        from security.services import create_audit_log
        job = type(job).objects.select_for_update().get(pk=job.pk)
        if actor.company_id != job.company_id or not CapabilityService.has(actor, Capabilities.IMPORT_EMPLOYEES):
            raise PermissionDenied("You cannot commit this import.")
        if job.status != "READY":
            raise ValidationError("Import is not ready.")

        if job.invalid_rows or not job.valid_rows:
            raise ValidationError("Correct all invalid rows before importing.")
        company = type(job.company).objects.select_for_update().get(pk=job.company_id)
        subscription = SubscriptionService.require_active(company)
        rows = job.validation_result.get("valid_rows", [])
        if cls.validate_rows(company=company, rows=rows)["errors"]:
            raise ValidationError("Some rows are no longer valid. Upload the file again.")
        from subscriptions.services import SubscriptionCapacity
        seats = SubscriptionCapacity.usage(company)["users"]
        if seats + len(rows) > subscription.plan.max_users:
            raise ValidationError("The plan does not have capacity for these employee accounts.")
        created = 0
        for row in job.validation_result.get("valid_rows", []):
            email = row["email"]
            user = User.objects.create(
                email=email,
                full_name=(
                    f"{row['first_name'].strip()} "
                    f"{row['last_name'].strip()}"
                ).strip(),
                company=job.company,
                is_active=False,
                role="EMPLOYEE",
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])

            EmployeeService.create_profile(
                user=user,
                employee_id=row["employee_id"].strip(),
                company=job.company,
                employment_type=row.get("employment_type", "FULL_TIME"),
                request=request,
            )

            CompanyInvite.objects.create(
                company=job.company,
                email=email,
                role=user.role,
                created_by=actor,
                expires_at=timezone.now() + timedelta(days=7),
            )
            created += 1

        job.status = "COMPLETED"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])
        create_audit_log(user=actor, company=company, request=request, action="IMPORT", obj=job,
                         description="Employee import completed.", metadata={"created":created})
        return created
