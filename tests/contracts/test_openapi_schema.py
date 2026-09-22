"""Release schema must generate cleanly and describe real API responses."""
import io
import json
import re

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from jsonschema import Draft202012Validator
from rest_framework.test import APIClient


@pytest.fixture(scope="module")
def schema():
    output = io.StringIO()
    call_command("spectacular", format="openapi-json", validate=True, fail_on_warn=True, stdout=output)
    return json.loads(output.getvalue())


def response_schema(schema, path, method, code):
    return schema["paths"][path][method]["responses"][str(code)]["content"]["application/json"]["schema"]


def validate_response(schema, path, method, response):
    # OpenAPI 3.0 nullable needs translation for a JSON Schema validator.
    def convert(value):
        if isinstance(value, list):
            return [convert(item) for item in value]
        if not isinstance(value, dict):
            return value
        converted = {key: convert(item) for key, item in value.items() if key != "nullable"}
        return {"anyOf": [converted, {"type": "null"}]} if value.get("nullable") else converted
    root = {**response_schema(schema, path, method, response.status_code), "components": schema["components"]}
    Draft202012Validator(convert(root)).validate(response.json())


def test_authentication_contracts_and_unique_operations(schema):
    login = schema["paths"]["/api/v1/auth/token/"]["post"]
    assert {"200", "202", "401", "503"} <= login["responses"].keys()
    assert "205" in schema["paths"]["/api/v1/logout/"]["post"]["responses"]
    otp = schema["components"]["schemas"]["OTPRequest"]
    assert otp["properties"]["code"]["type"] == "string"
    assert "email" not in otp["required"]
    ids = [operation["operationId"] for path in schema["paths"].values() for method, operation in path.items()
           if method in {"get", "post", "put", "patch", "delete"}]
    assert len(ids) == len(set(ids))
    assert "put" not in schema["paths"]["/api/platform/v1/administration/{key}/"]


def test_upload_export_and_computed_types(schema):
    imports = [operation for path, methods in schema["paths"].items() if "import" in path
               for method, operation in methods.items() if method == "post" and "requestBody" in operation]
    assert any("multipart/form-data" in op["requestBody"]["content"] for op in imports)
    assert any("text/csv" in op.get("responses", {}).get("200", {}).get("content", {})
               for methods in schema["paths"].values() for op in methods.values())
    user = schema["components"]["schemas"]["User"]["properties"]
    assert user["capabilities"]["type"] == "array"
    assert user["allowed_actions"]["type"] == "array"


@pytest.mark.django_db
def test_login_and_otp_responses_match_schema(schema, django_user_model, settings):
    from companies.models import Company
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.SECURE_SSL_REDIRECT = False
    cache.clear()
    company = Company.objects.create(name="Schema authentication")
    user = django_user_model.objects.create_user(email="schema-login@example.test", password="schema-password-123",
        company=company, is_active=True, email_verified=True, account_state="ACTIVE", role="EMPLOYEE")
    client = APIClient()
    login_path = "/api/v1/auth/token/"
    credentials = {"email": user.email, "password": "schema-password-123"}
    challenge = client.post(login_path, credentials, format="json")
    assert challenge.status_code == 202
    validate_response(schema, login_path, "post", challenge)
    code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
    otp_path = "/api/v1/auth/verify-otp/"
    verified = client.post(otp_path, {"challenge_id": challenge.data["challenge_id"], "code": code, "trust_device": True}, format="json")
    assert verified.status_code == 200
    validate_response(schema, otp_path, "post", verified)
    trusted = client.post(login_path, credentials, format="json", HTTP_X_SMARTBIZ_DEVICE_TOKEN=verified.data["trusted_device_token"])
    assert trusted.status_code == 200
    validate_response(schema, login_path, "post", trusted)


@pytest.mark.django_db
def test_dashboard_and_setup_responses_match_schema(schema, django_user_model, settings):
    from companies.models import Company
    settings.SECURE_SSL_REDIRECT = False
    company = Company.objects.create(name="Schema dashboard")
    user = django_user_model.objects.create_user(email="schema-admin@example.test", company=company,
        role="ADMIN", is_active=True, account_state="ACTIVE")
    client = APIClient()
    client.force_authenticate(user)
    for path in ("/api/v1/dashboard/", "/api/v1/company-setup/status/", "/api/v1/company-setup/health/"):
        response = client.get(path)
        assert response.status_code == 200, response.data
        validate_response(schema, path, "get", response)
