import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from companies.models import Branch, Company, WorkspacePurgeReceipt
from companies.purge import PurgePlan, purge_workspace, resume_file_cleanup
from documents.models import Attachment
from forms_engine.models import FormSubmission, FormTemplate
from organizations.models import Position
from platform_admin.models import SecurityIncident
from security.models import AuditLog

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def purge_case(django_user_model, settings, tmp_path):
    settings.SECURE_SSL_REDIRECT = False
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.WORKSPACE_PURGE_ENABLED = True
    settings.WORKSPACE_PURGE_BACKUP_RETENTION_DAYS = 30
    ledger = tmp_path / "ledger"; ledger.mkdir()
    settings.WORKSPACE_PURGE_LEDGER_DIR = str(ledger)
    now = timezone.now()
    company = Company.objects.create(name="Purge synthetic workspace", is_active=False, archived_at=now-timedelta(days=31), recovery_until=now-timedelta(days=1))
    other = Company.objects.create(name="Retained synthetic workspace")
    owner = django_user_model.objects.create_superuser(email="purge-owner@example.test", full_name="Owner", password="test-password")
    user = django_user_model.objects.create_user(email="purge-member@example.test", full_name="Member", password="test-password", company=company, role="ADMIN", is_active=True, email_verified=True)
    branch = Branch.objects.create(company=company, name="Head office")
    company.headquarters = branch; company.save(update_fields=["headquarters"])
    user.branch = branch; user.save(update_fields=["branch"])
    position = Position.objects.create(company=company, branch=branch, title="Director")
    template = FormTemplate.objects.create(company=company, name="Form", code="PURGE")
    revision = FormTemplate.objects.create(company=company, name="Revision", code="PURGE2", supersedes=template)
    submission = FormSubmission.objects.create(company=company, template=revision, submitted_by=user, reference_number="PURGE-1")
    other_template = FormTemplate.objects.create(company=other, name="Keep form", code="KEEP")
    ct = ContentType.objects.get_for_model(FormSubmission)
    attachment = Attachment.objects.create(company=company, content_type=ct, object_id=str(submission.pk), original_filename="proof.txt", uploaded_by=user)
    attachment.file.save("proof.txt", ContentFile(b"synthetic private evidence"))
    AuditLog.objects.create(company=company, user=user, action="SYNTHETIC", description="Synthetic private content")
    return SimpleNamespace(company=company, other=other, owner=owner, user=user, branch=branch,
        position=position, template=template, revision=revision, submission=submission,
        other_template=other_template, attachment=attachment, ledger=ledger)


def erase(case, fingerprint=None):
    return purge_workspace(company=case.company, actor=case.owner,
        values={"company_name": case.company.name, "password": "test-password", "reason": "Synthetic deletion check"},
        fingerprint=fingerprint or PurgePlan(case.company).fingerprint, acknowledge_backups=True)


def test_purge_removes_protected_graph_files_and_keeps_other_tenant_and_identity(purge_case):
    c = purge_case
    plan = PurgePlan(c.company)
    assert not plan.blockers, plan.blockers
    file_name = c.attachment.file.name; storage = c.attachment.file.storage
    company_id = c.company.pk
    receipt = erase(c, plan.fingerprint)
    assert receipt.status == "COMPLETE" and receipt.pending_files == []
    assert not Company.objects.filter(pk=company_id).exists()
    assert not FormSubmission.objects.filter(pk=c.submission.pk).exists()
    assert not Position.objects.filter(pk=c.position.pk).exists()
    assert not storage.exists(file_name)
    assert Company.objects.filter(pk=c.other.pk).exists()
    assert FormTemplate.objects.filter(pk=c.other_template.pk).exists()
    c.user.refresh_from_db()
    assert c.user.company_id is None and c.user.branch_id is None and not c.user.is_active
    assert c.user.role == "INDIVIDUAL" and c.user.email == "purge-member@example.test"
    marker = json.loads((c.ledger / f"{receipt.pk}.json").read_text())
    assert marker["workspace_id"] == company_id
    assert "name" not in marker
    assert AuditLog.objects.filter(action="WORKSPACE_LIVE_PURGE_COMPLETED", company__isnull=True).exists()


def test_retention_expiry_disabled_and_preview_change_block_erasure(purge_case, settings):
    c = purge_case
    fingerprint = PurgePlan(c.company).fingerprint
    Branch.objects.create(company=c.company, name="New archived row")
    with pytest.raises(ValidationError, match="changed"):
        erase(c, fingerprint)
    for field, value, fragment in (("deletion_hold_reason", "Hold for investigation", "retention hold"),
                                    ("recovery_until", timezone.now()+timedelta(days=1), "recovery period")):
        original = getattr(c.company, field)
        setattr(c.company, field, value); c.company.save(update_fields=[field])
        assert any(fragment in text for text in PurgePlan(c.company).blockers)
        with pytest.raises(ValidationError): erase(c)
        setattr(c.company, field, original); c.company.save(update_fields=[field])
    settings.WORKSPACE_PURGE_ENABLED = False
    with pytest.raises(ValidationError): erase(c)
    assert Company.objects.filter(pk=c.company.pk).exists() and c.attachment.file.storage.exists(c.attachment.file.name)
    assert not WorkspacePurgeReceipt.objects.exists()


def test_cross_company_fk_generic_reference_shared_file_and_incident_block(purge_case):
    c=purge_case
    external = FormSubmission.objects.create(company=c.other, template=c.template, reference_number="CROSS")
    assert any("outside this workspace" in item for item in PurgePlan(c.company).blockers)
    with pytest.raises(ValidationError): erase(c)
    external.delete()
    borrowed = Attachment.objects.create(company=c.other, content_type=c.attachment.content_type,
        object_id=str(c.submission.pk), original_filename="borrowed.txt", file=c.attachment.file.name)
    blockers = PurgePlan(c.company).blockers
    assert any("refers to its content" in item for item in blockers)
    assert any("file is shared" in item for item in blockers)
    borrowed.delete()
    SecurityIncident.objects.create(company=c.company, created_by=c.owner, title="Retained investigation")
    assert any("outside this workspace" in item for item in PurgePlan(c.company).blockers)
    with pytest.raises(ValidationError): erase(c)


def test_file_failure_is_not_success_and_retry_is_idempotent(purge_case):
    c=purge_case; storage=c.attachment.file.storage; name=c.attachment.file.name
    with patch.object(storage, "delete", side_effect=OSError("storage credential should never be logged")):
        receipt=erase(c)
    assert receipt.status == "FILES_PENDING" and receipt.failure_code == "FILE_CLEANUP_REQUIRED"
    assert not Company.objects.filter(pk=c.company.pk).exists() and storage.exists(name)
    assert "credential" not in receipt.failure_code
    receipt=resume_file_cleanup(receipt.pk, actor=c.owner)
    assert receipt.status == "COMPLETE" and not storage.exists(name)
    assert resume_file_cleanup(receipt.pk, actor=c.owner).status == "COMPLETE"


def test_roles_hold_confirmation_and_retry_routes(purge_case):
    c=purge_case; client=APIClient(); url=f"/api/platform/v1/workspace-deletion/{c.company.pk}/"
    client.force_authenticate(c.user)
    assert client.get(url+"preview/").status_code == 403
    assert client.post(url+"purge/", {}, format="json").status_code == 403
    client.force_authenticate(c.owner)
    values={"company_name":c.company.name, "reason":"Synthetic retention hold", "password":"test-password", "hold":True}
    bad=client.post(url+"hold/", {**values,"password":"wrong"}, format="json")
    assert bad.status_code == 400
    result=client.post(url+"hold/", values, format="json")
    assert result.status_code == 200 and not result.data["eligible"], result.data
    c.company.refresh_from_db(); assert c.company.deletion_hold_reason
    c.owner.platform_duty="SUPPORT"; c.owner.save(update_fields=["platform_duty"])
    assert client.get(url+"preview/").status_code == 403
    assert client.get("/api/platform/v1/workspace-purge-receipts/").status_code == 403


def test_backup_ledger_prevents_restored_workspace_recovery(purge_case):
    c=purge_case; old_id=c.company.pk
    receipt=erase(c)
    restored=Company.objects.create(pk=old_id, name="Synthetic restored backup")
    call_command("apply_workspace_deletion_ledger", directory=str(c.ledger))
    restored.refresh_from_db(); receipt.refresh_from_db()
    assert not restored.is_active and restored.archived_at and receipt.status == "BACKUP_BLOCKED"
    from companies.lifecycle import WorkspaceLifecycleService
    with pytest.raises(ValidationError, match="ledger"):
        WorkspaceLifecycleService.restore(company=restored, actor=c.owner,
            values={"company_name":restored.name, "reason":"Cannot resurrect erased data", "password":"test-password"})


def test_owner_purge_and_retry_api_confirmations(purge_case):
    c=purge_case; client=APIClient(); client.force_authenticate(c.owner)
    url=f"/api/platform/v1/workspace-deletion/{c.company.pk}/"
    preview=client.get(url+"preview/")
    assert preview.status_code == 200 and preview.data["eligible"], preview.data
    values={"company_name":c.company.name,"password":"test-password","reason":"Synthetic permanent deletion",
            "fingerprint":preview.data["fingerprint"],"acknowledge_backups":True}
    assert client.post(url+"purge/", {**values,"password":"wrong"}, format="json").status_code == 400
    assert client.post(url+"purge/", {**values,"acknowledge_backups":False}, format="json").status_code == 400
    with patch.object(c.attachment.file.storage,"delete",side_effect=OSError("Unavailable")):
        deleted=client.post(url+"purge/",values,format="json")
    assert deleted.status_code == 200 and deleted.data["status"] == "FILES_PENDING", deleted.data
    retry_url=f"/api/platform/v1/workspace-purge-receipts/{deleted.data['id']}/retry/"
    assert client.post(retry_url,{"password":"wrong","reason":"Retry"},format="json").status_code == 400
    retried=client.post(retry_url,{"password":"test-password","reason":"Storage restored"},format="json")
    assert retried.status_code == 200 and retried.data["status"] == "COMPLETE", retried.data
    assert "pending_files" not in retried.data


def test_late_cross_company_reference_rolls_back_database_and_preserves_files(purge_case):
    c=purge_case; original=QuerySet._raw_delete; inserted=False
    def introduce_reference(queryset, using):
        nonlocal inserted
        if not inserted:
            inserted=True
            FormSubmission.objects.create(company=c.other,template=c.template,reference_number="LATE-CROSS")
        return original(queryset,using)
    with patch.object(QuerySet,"_raw_delete",introduce_reference), pytest.raises(IntegrityError):
        erase(c)
    assert Company.objects.filter(pk=c.company.pk).exists()
    assert FormSubmission.objects.filter(pk=c.submission.pk).exists()
    assert FormTemplate.objects.filter(pk=c.other_template.pk).exists()
    assert not WorkspacePurgeReceipt.objects.exists()
    assert c.attachment.file.storage.exists(c.attachment.file.name)
    c.user.refresh_from_db(); assert c.user.company_id == c.company.pk


def test_ledger_failure_retains_cleanup_manifest_and_files(purge_case):
    c=purge_case
    with patch("companies.purge.write_deletion_marker",side_effect=OSError("Unavailable ledger")):
        receipt=erase(c)
    assert receipt.status == "FILES_PENDING" and receipt.failure_code == "DELETION_LEDGER_UNAVAILABLE"
    assert c.attachment.file.storage.exists(c.attachment.file.name)
    receipt=resume_file_cleanup(receipt.pk,actor=c.owner)
    assert receipt.status == "COMPLETE"
    assert json.loads((c.ledger/f"{receipt.pk}.json").read_text())["pending_files"] == []


def test_restored_backup_retains_cleanup_for_uploads_newer_than_the_backup(purge_case):
    c=purge_case; old_id=c.company.pk; name=c.attachment.file.name; storage=c.attachment.file.storage
    with patch.object(storage,"delete",side_effect=OSError("Unavailable storage")):
        receipt=erase(c)
    marker=json.loads((c.ledger/f"{receipt.pk}.json").read_text())
    assert marker["pending_files"]
    restored=Company.objects.create(pk=old_id,name="Restored company without newer upload metadata")
    call_command("apply_workspace_deletion_ledger",directory=str(c.ledger))
    restored.refresh_from_db(); receipt.refresh_from_db()
    assert receipt.pending_files and storage.exists(name)
    c.company=restored
    receipt=erase(c)
    assert receipt.status == "COMPLETE" and not storage.exists(name)


def test_unknown_inventory_and_unsafe_file_paths_block_deletion(purge_case):
    c=purge_case
    import companies.purge as module
    with patch.object(module,"DIRECT",module.DIRECT-{"forms_engine.formtemplate"}):
        assert any("inventory needs review" in text for text in PurgePlan(c.company).blockers)
        with pytest.raises(ValidationError): erase(c)
    Attachment.objects.filter(pk=c.attachment.pk).update(file="../outside-storage.txt")
    assert any("storage or a file path" in text for text in PurgePlan(c.company).blockers)
    with pytest.raises(ValidationError): erase(c)
