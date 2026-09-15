import pytest
from django.urls import resolve
from rest_framework.test import APIClient
from organizations.views import DepartmentViewSet, TeamViewSet, EmployeeProfileViewSet

@pytest.mark.parametrize("path,view", [("departments", DepartmentViewSet), ("teams", TeamViewSet), ("employees", EmployeeProfileViewSet)])
def test_organization_alias_uses_canonical_view(path, view):
    assert resolve(f"/api/v1/{path}/").func.cls is view
    assert resolve(f"/api/v1/organizations/{path}/").func.cls is view

@pytest.mark.django_db
def test_company_health_permission_and_response(django_user_model, settings):
    from companies.models import Company
    settings.SECURE_SSL_REDIRECT = False
    company = Company.objects.create(name="Setup regression")
    user = django_user_model.objects.create_user(email="setup@example.test", full_name="Setup", password="test-password", company=company, role="ADMIN", is_active=True, account_state="ACTIVE")
    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/v1/company-setup/health/")
    assert response.status_code == 200, response.data
    assert "checks" in response.data
    assert isinstance(response.data["issues"], list)
    assert response.data["completed_steps"] == []
    assert {issue["code"] for issue in response.data["issues"]} == {
        check["code"] for check in response.data["checks"] if not check["passed"]
    }
    valid_destinations = {"/settings/company-profile", "/branches", "/departments",
                          "/employees/positions", "/employees", "/settings/roles-permissions"}
    assert all(issue["url"] in valid_destinations for issue in response.data["issues"])
    for path in ("departments", "teams", "employees"):
        assert client.get(f"/api/v1/{path}/").status_code == 200
    for role in ("EMPLOYEE", "SUPERUSER"):
        user.role = role
        user.save(update_fields=["role"])
        assert client.get("/api/v1/company-setup/health/").status_code == 403

@pytest.mark.django_db
def test_onboarding_actions_and_template_application(django_user_model):
    from companies.models import Company
    from company_setup.models import CompanySetupState, BusinessSetupTemplate
    from organizations.models import Department
    company = Company.objects.create(name='Onboarding test')
    other = Company.objects.create(name='Other tenant')
    user = django_user_model.objects.create_user(email='onboarding@example.test', company=company, role='ADMIN', is_active=True, account_state='ACTIVE')
    client = APIClient()
    client.force_authenticate(user)
    base = '/api/v1/company-setup/'
    response = client.get(base+'status/')
    assert response.status_code == 200
    assert response.data['completed'] is False
    assert next(step for step in response.data['steps'] if step['code'] == 'company')['required'] is True
    assert client.post(base+'steps/skip/', {'step':'company','reason':'Later'}, format='json').status_code == 400
    assert client.post(base+'steps/skip/', {'step':'unknown','reason':'Later'}, format='json').status_code == 400
    assert client.post(base+'steps/skip/', {'step':[], 'reason':'Later'}, format='json').status_code == 400
    assert client.post(base+'steps/skip/', {'step':'template', 'reason':123}, format='json').status_code == 400
    assert client.post(base+'steps/complete/', {'step':[]}, format='json').status_code == 400
    assert client.post(base+'steps/skip/', {'step':'template','reason':' '}, format='json').status_code == 400
    assert client.post(base+'steps/skip/', {'step':'template','reason':'Manual configuration'}, format='json').status_code == 200
    assert client.post(base+'steps/complete/', {'step':'template'}, format='json').status_code == 200
    state = CompanySetupState.objects.get(company=company)
    assert 'template' in state.completed_steps and 'template' not in state.skipped_steps
    assert client.post(base+'steps/skip/', {'step':'template','reason':'Later'}, format='json').status_code == 400
    assert client.post(base+'steps/complete/', {'step':'finish'}, format='json').status_code == 400
    state.refresh_from_db()
    assert not state.onboarding_completed
    template = BusinessSetupTemplate.objects.create(code='example', name='Example', configuration={'departments':['Operations']})
    assert client.get(base+'templates/').status_code == 200
    for _ in range(2):
        response = client.post(base+'templates/example/apply/', {'departments':True,'positions':False,'document_categories':False}, format='json')
        assert response.status_code == 200, response.data
    assert Department.objects.filter(company=company, name='Operations').count() == 1
    assert not Department.objects.filter(company=other).exists()
    assert client.post(base+'templates/example/apply/', {'company':other.pk}, format='json').status_code == 400
    template.is_active = False
    template.save()
    assert client.post(base+'templates/example/apply/', {}, format='json').status_code == 404
    user.role = 'EMPLOYEE'
    user.save()
    assert client.get(base+'templates/').status_code == 403
    assert client.post(base+'templates/example/apply/', {}, format='json').status_code == 403
