import io
import uuid
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError as AnswerError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from companies.models import Company, Branch
from documents.services import validate_uploaded_file, MAX_ATTACHMENT_SIZE
from forms_engine.models import FormTemplate, FormField, FormSubmission
from forms_engine.services import FormSubmissionService
from forms_engine.validation import validate_rules
from forms_engine.versioning import FormTemplateVersionService as Versions


@pytest.mark.parametrize('kind,value', [
    ('DATE','2026-02-30'), ('DATE','not-a-date'), ('TIME','25:99'), ('DATETIME','tomorrow'),
    ('EMAIL','not-an-email'), ('INTEGER',1.9), ('INTEGER',True),
    ('DECIMAL','Infinity'), ('DECIMAL','NaN'), ('DECIMAL',False),
])
def test_invalid_typed_answers_are_rejected(kind, value):
    with pytest.raises(AnswerError):
        FormSubmissionService._validate_field(field=SimpleNamespace(field_type=kind, validation_rules={}, options=[]), value=value)


@pytest.mark.parametrize('kind,value', [('DATE','2026-10-12'), ('TIME','23:59'), ('DATETIME','2026-10-12T09:30'), ('DATETIME','2026-10-12T09:30:00+02:00'), ('EMAIL','worker@example.test'), ('INTEGER','2.0'), ('DECIMAL','2.75')])
def test_valid_typed_answers_still_work(kind, value):
    FormSubmissionService._validate_field(field=SimpleNamespace(field_type=kind, validation_rules={}, options=[]), value=value)


@pytest.mark.parametrize('rules', [{'min':'bad'}, {'max':'NaN'}, {'min':True}, {'min':3,'max':2}, {'min_length':-1}, {'max_length':1.2}, {'min_length':4,'max_length':2}])
def test_invalid_rules_fail_as_validation_errors(rules):
    with pytest.raises(AnswerError):
        validate_rules(rules)


def test_bounded_nan_and_required_whitespace_are_safe():
    with pytest.raises(AnswerError):
        FormSubmissionService._validate_field(field=SimpleNamespace(field_type='DECIMAL',validation_rules={'min':0},options=[]),value='NaN')
    schema={'fields':[{'key':'note','label':'Note','field_type':'TEXT','required':True}]}
    with pytest.raises(AnswerError):
        FormSubmissionService.validate_data(template=Mock(),data={'note':'   '},schema=schema)


@pytest.mark.parametrize('name,content', [('fake.pdf',b'MZ renamed executable'), ('fake.png',b'<svg>not a PNG</svg>'), ('fake.docx',b'not a ZIP'), ('fake.txt',b'\x00binary')])
def test_renamed_or_binary_uploads_are_rejected(name, content, settings):
    settings.ATTACHMENT_SCANNER=''; settings.ATTACHMENT_SCAN_REQUIRED=False
    with pytest.raises(ValidationError):
        validate_uploaded_file(SimpleUploadedFile(name,content),max_size=MAX_ATTACHMENT_SIZE)


def test_real_documents_preserve_stream_and_office_limits(settings):
    settings.ATTACHMENT_SCANNER=''; settings.ATTACHMENT_SCAN_REQUIRED=False
    from PIL import Image
    image=io.BytesIO(); Image.new('RGB',(2,2)).save(image,format='PNG')
    file=SimpleUploadedFile('image.png',image.getvalue()); file.seek(3)
    assert validate_uploaded_file(file,max_size=MAX_ATTACHMENT_SIZE)=='image/png'
    assert file.tell()==3
    archive=io.BytesIO()
    types='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    document='<document xmlns="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    with zipfile.ZipFile(archive,'w') as output:
        output.writestr('[Content_Types].xml',types)
        output.writestr('word/document.xml',document)
    assert validate_uploaded_file(SimpleUploadedFile('document.docx',archive.getvalue()),max_size=MAX_ATTACHMENT_SIZE)
    unsafe=io.BytesIO()
    with zipfile.ZipFile(unsafe,'w') as output:
        output.writestr('[Content_Types].xml',types)
        output.writestr('word/document.xml',document)
        output.writestr('../outside.txt','bad')
    with pytest.raises(ValidationError):
        validate_uploaded_file(SimpleUploadedFile('document.docx',unsafe.getvalue()),max_size=MAX_ATTACHMENT_SIZE)


def test_required_scanner_fails_closed_and_restores_stream(settings, monkeypatch):
    settings.ATTACHMENT_SCAN_REQUIRED=True; settings.ATTACHMENT_SCANNER=''
    file=SimpleUploadedFile('note.txt',b'valid UTF-8 text')
    with pytest.raises(ValidationError):
        validate_uploaded_file(file,max_size=MAX_ATTACHMENT_SIZE)
    settings.ATTACHMENT_SCANNER='test.scanner'
    verdict=Mock(return_value=False)
    monkeypatch.setattr('documents.file_validation.import_string',lambda _:verdict)
    with pytest.raises(ValidationError):
        validate_uploaded_file(file,max_size=MAX_ATTACHMENT_SIZE)
    verdict.side_effect=OSError('Private scanner connection details')
    with pytest.raises(ValidationError) as exc:
        validate_uploaded_file(file,max_size=MAX_ATTACHMENT_SIZE)
    assert 'Private scanner' not in str(exc.value)
    verdict.side_effect=None; verdict.return_value=True
    file.seek(4)
    validate_uploaded_file(file,max_size=MAX_ATTACHMENT_SIZE)
    assert file.tell()==4


def test_pdf_structure_and_encryption(settings):
    from pypdf import PdfWriter
    settings.ATTACHMENT_SCANNER=''; settings.ATTACHMENT_SCAN_REQUIRED=False
    writer=PdfWriter(); writer.add_blank_page(width=100,height=100)
    stream=io.BytesIO();writer.write(stream)
    assert validate_uploaded_file(SimpleUploadedFile('receipt.pdf',stream.getvalue()),max_size=MAX_ATTACHMENT_SIZE)=='application/pdf'
    with pytest.raises(ValidationError):
        validate_uploaded_file(SimpleUploadedFile('fake.pdf',b'%PDF-1.7\nnot a PDF\n%%EOF'),max_size=MAX_ATTACHMENT_SIZE)
    writer.encrypt('test-only');stream=io.BytesIO();writer.write(stream)
    with pytest.raises(ValidationError):
        validate_uploaded_file(SimpleUploadedFile('locked.pdf',stream.getvalue()),max_size=MAX_ATTACHMENT_SIZE)


@pytest.mark.parametrize('source_type,expected', [('BOOLEAN','Yes'),('SELECT','missing'),('MULTISELECT','one')])
def test_conditions_require_supported_saved_answers(source_type, expected):
    fields=[{'key':'source','label':'Source','field_type':source_type,'options':[{'value':'one','label':'One'}]}, {'key':'follow_up','label':'Follow up','field_type':'TEXT','validation_rules':{'show_when':{'field':'source','equals':expected}}}]
    with pytest.raises(ValidationError):
        Versions.validate(actor=None,company=None,data={},fields=fields,starter=True)


def test_clamav_clean_verdict_is_explicit(settings, monkeypatch):
    from documents.scanning import clamav
    class Connection:
        def __init__(self, response): self.response=response;self.sent=[]
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def settimeout(self,value): pass
        def sendall(self,data): self.sent.append(data)
        def recv(self,size): result=self.response;self.response=b'';return result
    connection=Connection(b'stream: OK\0')
    monkeypatch.setattr('documents.scanning.socket.create_connection',lambda *args,**kwargs:connection)
    assert clamav(io.BytesIO(b'test bytes')) is True
    assert connection.sent[0]==b'zINSTREAM\0'
    connection.response=b'stream: FOUND\0'
    assert clamav(io.BytesIO(b'test bytes')) is False


def template_for(company, actor, code='review', **kwargs):
    template=FormTemplate.objects.create(company=company,created_by=actor,name='Review form',code=code,**kwargs)
    FormField.objects.create(template=template,key='note',label='Note',field_type='TEXT',required=True)
    return template


@pytest.mark.django_db
def test_create_retry_is_actor_tenant_bound_and_never_overwrites(django_user_model):
    company=Company.objects.create(name='Retry tenant')
    author=django_user_model.objects.create_user(email='retry-author@test.local',company=company,role='ADMIN',is_active=True)
    peer=django_user_model.objects.create_user(email='retry-peer@test.local',company=company,role='ADMIN',is_active=True)
    template=template_for(company,author); Versions.publish(template=template,actor=author)
    key=str(uuid.uuid4()); client=APIClient(); client.force_authenticate(author)
    payload={'template':str(template.pk),'client_request_id':key,'data':{'note':'Original'}}
    first=client.post('/api/v1/form-submissions/',payload,format='json'); assert first.status_code==201,first.data
    payload['data']={'note':'Retry must not overwrite'}
    second=client.post('/api/v1/form-submissions/',payload,format='json'); assert second.status_code==201,second.data
    assert second.data['id']==first.data['id']
    assert FormSubmission.objects.get(pk=first.data['id']).data['note']=='Original'
    other_template=template_for(company,author,code='other'); Versions.publish(template=other_template,actor=author)
    payload['template']=str(other_template.pk)
    assert client.post('/api/v1/form-submissions/',payload,format='json').status_code==400
    payload['template']=str(template.pk); client.force_authenticate(peer)
    third=client.post('/api/v1/form-submissions/',payload,format='json'); assert third.status_code==201,third.data
    assert third.data['id']!=first.data['id']
    foreign=Company.objects.create(name='Other retry tenant')
    outsider=django_user_model.objects.create_user(email='retry-other@test.local',company=foreign,role='ADMIN',is_active=True)
    foreign_template=template_for(foreign,outsider); Versions.publish(template=foreign_template,actor=outsider)
    client.force_authenticate(outsider); payload['template']=str(foreign_template.pk)
    fourth=client.post('/api/v1/form-submissions/',payload,format='json'); assert fourth.status_code==201,fourth.data
    assert fourth.data['id'] not in [first.data['id'],third.data['id']]
    assert client.get(f"/api/v1/form-submissions/{first.data['id']}/").status_code==404
    assert client.get('/api/v1/form-submissions/',{'search':'Review form','status':'DRAFT'}).data['count']==1
    assert client.get('/api/v1/form-submissions/',{'status':'invalid'}).status_code==400


@pytest.mark.django_db
def test_publication_preserves_restrictions_and_requires_broadening_confirmation(django_user_model):
    company=Company.objects.create(name='Deliberate publication')
    actor=django_user_model.objects.create_user(email='deliberate@test.local',company=company,role='ADMIN',is_active=True)
    branch=Branch.objects.create(company=company,name='Restricted branch')
    template=template_for(company,actor,branch=branch,audience_user_ids=[str(actor.pk)])
    settings={'audience':'COMPANY','entry_visibility':'STANDARD'}
    Versions.publish(template=template,actor=actor,publication=settings)
    template.refresh_from_db(); assert template.branch_id==branch.pk and template.audience_user_ids==[str(actor.pk)]
    revision=Versions.revise(template=template,actor=actor,data={})
    with pytest.raises(ValidationError):
        Versions.publish(template=revision,actor=actor,publication={**settings,'preserve_restrictions':False})
    revision.refresh_from_db(); assert revision.lifecycle_status=='DRAFT'
    Versions.publish(template=revision,actor=actor,publication={**settings,'preserve_restrictions':False,'confirm_audience_change':True})
    revision.refresh_from_db(); assert revision.branch_id is None and revision.audience_user_ids==[]


@pytest.mark.django_db
def test_ready_request_requires_explicit_no_approval_decision(django_user_model):
    company=Company.objects.create(name='Approval intent')
    actor=django_user_model.objects.create_user(email='intent@test.local',company=company,role='ADMIN',is_active=True)
    template=template_for(company,actor,category='REQUEST',source_starter='expense-request')
    with pytest.raises(ValidationError):
        Versions.publish(template=template,actor=actor)
    Versions.publish(template=template,actor=actor,publication={'audience':'COMPANY','entry_visibility':'STANDARD','confirm_no_approval':True})


@pytest.mark.django_db
def test_amount_library_migration_preserves_customizations_and_company_copies(django_user_model):
    import importlib
    from copy import deepcopy
    from django.apps import apps
    from django.db import connection
    from forms_engine.models import FormStarter
    migration = importlib.import_module('forms_engine.migrations.0021_nonnegative_library_amounts')
    original = deepcopy(migration.OLD_FIELDS[0]['field'])
    starter, _ = FormStarter.objects.update_or_create(code='payment-collection', defaults={'name':'Payment', 'field_schema':[original]})
    company = Company.objects.create(name='Preserved monetary copy')
    actor = django_user_model.objects.create_user(email='amount-copy@test.local', company=company, role='ADMIN')
    template = template_for(company, actor)
    before = list(template.fields.values())
    editor = SimpleNamespace(connection=connection)
    migration.update_catalogue(apps, editor)
    starter.refresh_from_db()
    assert starter.field_schema[0]['validation_rules']['min'] == 0
    assert list(template.fields.values()) == before
    original['label'] = 'Company-approved custom label'
    starter.field_schema = [original]; starter.save()
    migration.update_catalogue(apps, editor)
    starter.refresh_from_db()
    assert 'min' not in starter.field_schema[0]['validation_rules']
