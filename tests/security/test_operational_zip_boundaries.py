from types import SimpleNamespace
import pytest
from rest_framework.test import APIClient
from django.contrib.contenttypes.models import ContentType
from companies.models import Company
from planning.models import CompanyPlan, PlanItem
from workflows.models import WorkflowDefinition, WorkflowInstance
from workflows.views import WorkflowInstanceViewSet, WorkflowDefinitionViewSet
from requests_app.serializers import BusinessRequestSerializer

@pytest.mark.django_db
def test_private_plan_items_and_foreign_relations(django_user_model):
    company=Company.objects.create(name="Plan scope")
    other=Company.objects.create(name="Other plan scope")
    admin=django_user_model.objects.create_user(email="scope-admin@test.example",company=company,role="ADMIN")
    owner=django_user_model.objects.create_user(email="scope-owner@test.example",company=company)
    foreign=django_user_model.objects.create_user(email="scope-foreign@test.example",company=other)
    plan=CompanyPlan.objects.create(company=company,title="Private",plan_type="MONTHLY",visibility="PRIVATE",owner=owner,start_date="2026-09-01",end_date="2026-09-30")
    item=PlanItem.objects.create(plan=plan,title="Hidden")
    client=APIClient(); client.force_authenticate(admin)
    assert client.get(f"/api/v1/plan-items/{item.pk}/").status_code == 404
    assert client.post("/api/v1/plan-items/",{"plan":str(plan.pk),"title":"Injection"}).status_code == 400
    plan.visibility="COMPANY";plan.save()
    assert client.get(f"/api/v1/plan-items/{item.pk}/").status_code == 200
    assert client.patch(f"/api/v1/plan-items/{item.pk}/",{"owner":str(foreign.pk)}).status_code == 400
    assert client.patch(f"/api/v1/plan-items/{item.pk}/",{"title":"Allowed"}).status_code == 200

@pytest.mark.django_db
def test_workflow_visibility_is_participant_scoped(django_user_model):
    company=Company.objects.create(name="Workflow scope")
    admin=django_user_model.objects.create_user(email="wf-admin@test.example",company=company,role="ADMIN")
    author=django_user_model.objects.create_user(email="wf-author@test.example",company=company)
    platform=django_user_model.objects.create_superuser(email="wf-platform@test.example",password="test-pass-123",full_name="Platform")
    workflow=WorkflowDefinition.objects.create(company=company,name="Review",code="REVIEW",target_type="REQUEST")
    row=WorkflowInstance.objects.create(company=company,workflow=workflow,content_type=ContentType.objects.get_for_model(Company),object_id=str(company.pk),submitted_by=author)
    view=WorkflowInstanceViewSet()
    for user,expected in [(admin,False),(author,True),(platform,False)]:
        view.request=SimpleNamespace(user=user)
        assert view.get_queryset().filter(pk=row.pk).exists() == expected
    definitions=WorkflowDefinitionViewSet();definitions.request=SimpleNamespace(user=platform)
    assert not definitions.get_queryset().exists()

@pytest.mark.django_db
def test_request_validation_rejects_missing_company(django_user_model):
    from rest_framework.exceptions import ValidationError
    user=django_user_model.objects.create_user(email="no-company@test.example")
    serializer=BusinessRequestSerializer(context={"request":SimpleNamespace(user=user)})
    with pytest.raises(ValidationError,match="Tenant company context"):
        serializer.validate({})
