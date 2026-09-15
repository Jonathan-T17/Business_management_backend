from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.capabilities import Capabilities as C
from companies.models import Company
from organizations.models import UserCapabilityGrant
from projects.models import Project
from records_management.models import OfficialRecord, RecordExport
from data_tools.models import ImportJob
from data_tools.serializers import ImportJobSerializer


def test_import_summary_excludes_raw_upload_and_validation_data():
    data = ImportJobSerializer(ImportJob(validation_result={'valid_rows': [{'email': 'private@example.test'}]})).data
    assert 'file' not in data
    assert 'validation_result' not in data


@pytest.mark.django_db
def test_secondary_permissions_require_tenant_capabilities(django_user_model):
    from analytics_ai.permissions import IsAnalyticsAdmin
    from documents.permissions import CanManageDocuments, CanUseAttachments
    company = Company.objects.create(name='Secondary permissions')
    user = django_user_model.objects.create_user(email='secondary@example.test', company=company, role='EMPLOYEE')
    request = SimpleNamespace(user=user)
    assert not IsAnalyticsAdmin().has_permission(request, None)
    assert not CanManageDocuments().has_permission(request, None)
    assert CanUseAttachments().has_permission(request, None)
    for cap in (C.VIEW_COMPANY_ANALYTICS, C.MANAGE_DOCUMENTS):
        UserCapabilityGrant.objects.create(company=company, user=user, capability=cap)
    assert IsAnalyticsAdmin().has_permission(request, None)
    assert CanManageDocuments().has_permission(request, None)
    user.is_superuser = True
    assert not IsAnalyticsAdmin().has_permission(request, None)
    assert not CanManageDocuments().has_permission(request, None)
    assert not CanUseAttachments().has_permission(request, None)


@pytest.mark.django_db
def test_record_detail_hides_snapshots_and_export_requires_purpose(django_user_model):
    company = Company.objects.create(name='Record export')
    user = django_user_model.objects.create_user(email='record-export@example.test', company=company, role='ADMIN')
    project = Project.objects.create(company=company, name='Visible source', created_by=user)
    record = OfficialRecord.objects.create(company=company, record_type='OTHER', record_number='REC-1',
        title='Official record', content_type=ContentType.objects.get_for_model(project), object_id=str(project.pk),
        issued_at=timezone.now(), issued_by=user, snapshot={'private': 'value'}, approval_snapshot=[{'private': 'approval'}])
    client = APIClient()
    client.force_authenticate(user)
    root = f'/api/v1/official-records/{record.pk}/'
    response = client.get(root)
    assert response.status_code == 200, response.data
    assert 'snapshot' not in response.data and 'approval_snapshot' not in response.data
    assert 'EXPORT' not in response.data['allowed_actions']
    assert client.get(root + 'pdf/', {'purpose': 'Review'}).status_code == 403
    UserCapabilityGrant.objects.create(company=company, user=user, capability=C.EXPORT_OFFICIAL_RECORDS)
    assert 'EXPORT' in client.get(root).data['allowed_actions']
    for purpose in ('', ' ', 'x' * 256):
        assert client.get(root + 'pdf/', {'purpose': purpose}).status_code == 400
    assert not RecordExport.objects.filter(record=record).exists()
    response = client.get(root + 'pdf/', {'purpose': ' Quarterly review '})
    assert response.status_code == 200
    assert b''.join(response.streaming_content).startswith(b'%PDF')
    assert RecordExport.objects.get(record=record).purpose == 'Quarterly review'
    record.refresh_from_db()
    assert record.snapshot == {'private': 'value'}
