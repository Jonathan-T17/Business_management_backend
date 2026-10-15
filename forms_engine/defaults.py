"""Trusted starting values; shared previews never call this with tenant data."""
from core.sequence import company_local_date
from rest_framework.exceptions import ValidationError

SOURCES = {"USER_NAME": "TEXT", "COMPANY_NAME": "TEXT", "BRANCH_NAME": "TEXT", "TODAY": "DATE", "COMPANY_CURRENCY": "TEXT"}
LOCKED = {"USER_NAME", "COMPANY_NAME"}


def fields_of(schema):
    return schema.get("fields", []) if isinstance(schema, dict) else schema


def initial_values(schema, user, *, branch=None, date=None):
    company = user.company
    branch = branch or getattr(user, "branch", None)
    if branch and branch.company_id != company.pk:
        raise ValidationError("The location must belong to your company.")
    source_values = {
        "USER_NAME": user.full_name or user.email,
        "COMPANY_NAME": company.name,
        "BRANCH_NAME": branch.name if branch else "",
        "TODAY": str(date or company_local_date(company)),
        "COMPANY_CURRENCY": getattr(company, "default_currency", "") or "",
    }
    values = {}
    for field in fields_of(schema):
        source = field.get("validation_rules", {}).get("default_source")
        if source in source_values and source_values[source]:
            values[field["key"]] = source_values[source]
    return values


def apply_defaults(schema, user, data, *, existing=None, branch=None, date=None):
    if data is not None and not isinstance(data, dict):
        raise ValidationError({"data": "Form answers must be an object."})
    values = initial_values(schema, user, branch=branch, date=date)
    result = dict(data or {})
    for field in fields_of(schema):
        key = field["key"]
        source = field.get("validation_rules", {}).get("default_source")
        if source not in SOURCES:
            continue
        if source in LOCKED:
            # A saved identity stays stable when the employee later edits their profile.
            trusted = existing.get(key) if existing and key in existing else values.get(key)
            if trusted is not None:
                result[key] = trusted
        elif existing is None and key not in result and key in values:
            result[key] = values[key]
    return result
