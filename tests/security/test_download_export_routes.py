import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from companies.models import Company
from documents.models import Document, DocumentVersion, DocumentCategory
from security.models import AuditLog
from data_tools.models import DataExportLog

@pytest.mark.django_db
def test_document_download_scoping_and_current_version(django_user_model, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    company = Company.objects.create(name='Download company')
    other = Company.objects.create(name='Other download company')
    user = django_user_model.objects.create_user(email='reader@example.test',company=company,role='ADMIN')
    client = APIClient(); client.force_authenticate(user)
    document = Document.objects.create(company=company,title='Document',current_version=2)
    for number, content in [(1,b'old'),(2,b'current')]:
        DocumentVersion.objects.create(document=document,version_number=number,file=SimpleUploadedFile(f'v{number}.txt',content),original_filename=f'v{number}.txt')
    url = f'/api/v1/documents/{document.pk}/download/'
    response = client.get(url)
    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'current'
    assert response['Cache-Control'] == 'private, no-store'
    assert AuditLog.objects.filter(action='DOWNLOAD',object_id=str(document.pk)).exists()
    category = DocumentCategory.objects.create(company=company,name='Sensitive',sensitive=True)
    document.category = category; document.save()
    assert client.get(url).status_code in (403,404)
    document.category = None; document.company = other; document.save()
    assert client.get(url).status_code == 404
    document.company = company; document.current_version = 3; document.save()
    assert client.get(url).status_code == 404

@pytest.mark.django_db
def test_export_requires_and_records_purpose(django_user_model):
    company = Company.objects.create(name='Export company')
    user = django_user_model.objects.create_user(email='export@example.test',company=company,role='ADMIN')
    client = APIClient(); client.force_authenticate(user)
    from organizations.models import UserCapabilityGrant
    from core.capabilities import Capabilities
    url = '/api/v1/exports/business-requests.csv'
    assert client.get(url, {'purpose':'Review'}).status_code == 403
    UserCapabilityGrant.objects.create(company=company,user=user,capability=Capabilities.EXPORT_OPERATIONAL_DATA)
    assert client.get(url).status_code == 400
    response = client.get(url,{'purpose':'Monthly review'})
    assert response.status_code == 200, getattr(response,'data',None)
    if response.streaming: list(response.streaming_content)
    assert DataExportLog.objects.get(company=company).filters['purpose'] == 'Monthly review'
    user.role = 'SUPERUSER'; user.save()
    assert client.get(url,{'purpose':'Review'}).status_code == 403
