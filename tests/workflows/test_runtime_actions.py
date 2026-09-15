import pytest
from rest_framework.exceptions import ValidationError

from companies.models import Company
from requests_app.models import BusinessRequest
from workflows.models import WorkflowDefinition, WorkflowStepDefinition
from workflows.runtime_service import WorkflowRuntimeService


@pytest.mark.django_db
@pytest.mark.parametrize("action,outcome", [("approve", "APPROVED"), ("reject", "REJECTED"), ("return_for_changes", "RETURNED")])
def test_workflow_actions_update_source_once(action, outcome, django_user_model):
    company = Company.objects.create(name="Workflow regression")
    author = django_user_model.objects.create_user(email="author@example.test", company=company, role="EMPLOYEE", is_active=True)
    reviewer = django_user_model.objects.create_user(email="reviewer@example.test", company=company, role="EMPLOYEE", is_active=True)
    workflow = WorkflowDefinition.objects.create(company=company, name="Review", code="REVIEW", target_type="REQUEST")
    WorkflowStepDefinition.objects.create(workflow=workflow, name="Review", order=1,
        recipient_type="USER", recipient_user=reviewer, notify_email=False)
    source = BusinessRequest.objects.create(company=company, requester=author, title="Purchase",
        description="Required equipment", request_number="TEST-1", request_type="PURCHASE")
    instance = WorkflowRuntimeService.start(workflow=workflow, target=source, submitted_by=author)
    assert instance.steps.get().routing_snapshot["recipient_type"] == "USER"
    method = getattr(WorkflowRuntimeService, action)
    method(instance=instance, actor=reviewer, note="Reviewed")
    source.refresh_from_db()
    instance.refresh_from_db()
    assert source.status == outcome
    assert instance.status == outcome
    with pytest.raises(ValidationError):
        method(instance=instance, actor=reviewer, note="Duplicate")
