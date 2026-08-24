import re

from django.core.exceptions import ValidationError


def validate_company_name(name):

    if len(name) < 3:
        raise ValidationError(
            "Company name is too short."
        )


def validate_phone(phone):

    pattern = r"^\+?[0-9]{10,15}$"

    if not re.match(pattern, phone):

        raise ValidationError(
            "Invalid phone number."
        )