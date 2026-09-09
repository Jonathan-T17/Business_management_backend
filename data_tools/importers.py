import csv
import io
from datetime import timedelta

from django.core.exceptions import ValidationError
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
        existing_emails = set(company.users.values_list("email", flat=True))
        existing_ids = set(EmployeeProfile.objects.values_list("employee_id", flat=True))
        for index, row in enumerate(rows, start=2):
            row = {str(key).strip(): value for key, value in row.items()}
            email = str(row.get("email", "")).strip().lower()
            employee_id = str(row.get("employee_id", "")).strip()
            row_errors = []
            for field in ("email", "employee_id", "first_name", "last_name"):
                if not str(row.get(field, "")).strip():
                    row_errors.append({"field": field, "message": f"{field.replace('_', ' ').title()} is required."})
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
        if file.name.lower().endswith(".xlsx"):
            from openpyxl import load_workbook

            workbook = load_workbook(file, read_only=True, data_only=True)
            rows = list(workbook.active.values)
            if not rows:
                return []
            headers = [
                str(value).strip() if value is not None else ""
                for value in rows[0]
            ]
            return [dict(zip(headers, row)) for row in rows[1:]]
        if file.name.lower().endswith(".csv"):
            return list(csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig")))
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

        if job.status != "READY":
            raise ValidationError("Import is not ready.")

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
        return created