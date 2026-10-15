from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from companies.models import Company, Branch
from documents.models import Document, DocumentCategory
from documents.serializers import DocumentSerializer
from notifications.models import Notification
from projects.models import Project, ProjectMembership
from reports.models import Report
from reports.views import ReportViewSet, ReportCommentViewSet


@pytest.fixture
def privacy_context(django_user_model, settings):
    settings.ATTACHMENT_SCAN_REQUIRED = False
    settings.ATTACHMENT_SCANNER = ''
    home = Company.objects.create(name='Privacy home')
    other = Company.objects.create(name='Privacy other')
    author = django_user_model.objects.create_user(email='privacy-author@test.local', company=home, role='EMPLOYEE', is_active=True)
    peer = django_user_model.objects.create_user(email='privacy-peer@test.local', company=home, role='EMPLOYEE', is_active=True)
    foreign = django_user_model.objects.create_user(email='privacy-foreign@test.local', company=other, role='EMPLOYEE', is_active=True)
    return home, other, author, peer, foreign


def document_serializer(author, **extra):
    return DocumentSerializer(data={'title': 'Privacy test', 'initial_file': SimpleUploadedFile('test.txt', b'Test document'), **extra}, context={'request': SimpleNamespace(user=author)})


@pytest.mark.django_db
def test_document_rejects_foreign_relationships(privacy_context):
    home, other, author, peer, foreign = privacy_context
    category = DocumentCategory.objects.create(company=other, name='Foreign')
    branch = Branch.objects.create(company=other, name='Foreign branch')
    serializer = document_serializer(author, category=category.pk, owner=foreign.pk, branch=branch.pk)
    assert not serializer.is_valid()
    assert {'category', 'owner', 'branch'} <= serializer.errors.keys()


@pytest.mark.django_db
def test_category_default_and_private_owner(privacy_context):
    home, other, author, peer, foreign = privacy_context
    category = DocumentCategory.objects.create(company=home, name='Management', default_visibility='MANAGEMENT')
    serializer = document_serializer(author, category=category.pk)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['visibility'] == 'MANAGEMENT'
    assert serializer.validated_data['owner'] == author
    private = document_serializer(author, visibility='PRIVATE')
    assert private.is_valid(), private.errors
    assert private.validated_data['owner'] == author


@pytest.mark.django_db
@pytest.mark.parametrize('visibility,field', [('BRANCH', 'branch'), ('DEPARTMENT', 'department'), ('TEAM', 'team')])
def test_scoped_document_requires_target(privacy_context, visibility, field):
    serializer = document_serializer(privacy_context[2], visibility=visibility)
    assert not serializer.is_valid()
    assert field in serializer.errors


@pytest.mark.django_db
def test_partial_document_edit_validates_retained_scope(privacy_context):
    home, other, author, peer, foreign = privacy_context
    branch = Branch.objects.create(company=home, name='Home branch')
    document = Document.objects.create(company=home, title='Existing', owner=author, visibility='BRANCH', branch=branch)
    serializer = DocumentSerializer(document, data={'branch': None}, partial=True, context={'request': SimpleNamespace(user=author)})
    assert not serializer.is_valid()
    assert 'branch' in serializer.errors
    safe = DocumentSerializer(document, data={'title': 'Renamed'}, partial=True, context={'request': SimpleNamespace(user=author)})
    assert safe.is_valid(), safe.errors
    full = DocumentSerializer(document, data={'title': 'Updated', 'visibility': 'PRIVATE', 'owner': author.pk}, context={'request': SimpleNamespace(user=author)})
    assert full.is_valid(), full.errors


@pytest.mark.django_db
def test_private_upload_saves_owned_initial_version(privacy_context, settings, tmp_path):
    from core.visibility import VisibilityService
    settings.MEDIA_ROOT = tmp_path
    author, peer = privacy_context[2:4]
    serializer = document_serializer(author, visibility='PRIVATE')
    assert serializer.is_valid(), serializer.errors
    document = serializer.save()
    assert document.owner == author
    assert document.versions.count() == 1
    assert VisibilityService.documents_queryset(user=author, queryset=Document.objects.all()).filter(pk=document.pk).exists()
    assert not VisibilityService.documents_queryset(user=peer, queryset=Document.objects.all()).filter(pk=document.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize('visibility', ['BRANCH', 'MANAGEMENT'])
def test_document_owner_keeps_access_after_choosing_a_restricted_audience(privacy_context, visibility):
    from core.visibility import VisibilityService
    home, other, author, peer, foreign = privacy_context
    branch = Branch.objects.create(company=home, name='Shared branch')
    document = Document.objects.create(company=home, title='Owned upload', owner=author, created_by=author, visibility=visibility, branch=branch)
    assert VisibilityService.documents_queryset(user=author, queryset=Document.objects.all()).filter(pk=document.pk).exists()
    assert not VisibilityService.documents_queryset(user=peer, queryset=Document.objects.all()).filter(pk=document.pk).exists()
    assert not VisibilityService.documents_queryset(user=foreign, queryset=Document.objects.all()).filter(pk=document.pk).exists()


@pytest.mark.django_db
def test_document_rejects_reversed_dates(privacy_context):
    serializer = document_serializer(privacy_context[2], effective_date='2026-10-13', expiry_date='2026-10-12')
    assert not serializer.is_valid()
    assert 'expiry_date' in serializer.errors


@pytest.mark.django_db
def test_document_creation_requires_the_upload_contract(privacy_context):
    serializer = DocumentSerializer(data={'title': 'Missing file', 'file': SimpleUploadedFile('test.txt', b'Test')}, context={'request': SimpleNamespace(user=privacy_context[2])})
    assert not serializer.is_valid()
    assert 'initial_file' in serializer.errors


@pytest.mark.django_db
def test_report_notifications_respect_state_and_visibility(privacy_context):
    home, other, author, peer, foreign = privacy_context
    project = Project.objects.create(company=home, name='Notification project', created_by=author)
    ProjectMembership.objects.create(project=project, user=peer)
    ProjectMembership.objects.create(project=project, user=foreign)
    report = Report.objects.create(company=home, project=project, created_by=author, title='Private title', description='Test', visibility='PRIVATE', status='DRAFT')
    view = ReportViewSet()
    view.request = SimpleNamespace(user=author)
    view._notify_report_submitted(report)
    assert not Notification.objects.filter(reference_id=str(report.pk)).exists()
    report.status = 'SUBMITTED'
    report.save()
    view._notify_report_submitted(report)
    assert not Notification.objects.filter(reference_id=str(report.pk)).exists()
    report.visibility = 'COMPANY'
    report.save()
    view._notify_report_submitted(report)
    assert Notification.objects.filter(recipient=peer, reference_id=str(report.pk)).count() == 1
    assert not Notification.objects.filter(recipient=foreign, reference_id=str(report.pk)).exists()


@pytest.mark.django_db
def test_private_comment_notification_excludes_project_peers(privacy_context):
    home, other, author, peer, foreign = privacy_context
    project = Project.objects.create(company=home, name='Comment project', created_by=author)
    ProjectMembership.objects.create(project=project, user=peer)
    report = Report.objects.create(company=home, project=project, created_by=author, title='Private comment title', description='Test', visibility='PRIVATE')
    comment = SimpleNamespace(report=report)
    view = ReportCommentViewSet()
    view.request = SimpleNamespace(user=author)
    view._notify_comment(comment)
    assert not Notification.objects.filter(reference_id=str(report.pk)).exists()
    view.request = SimpleNamespace(user=peer)
    view._notify_comment(comment)
    assert Notification.objects.filter(recipient=author, reference_id=str(report.pk)).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize('action', ['update', 'delete'])
def test_critical_report_escalations_do_not_disclose_private_reports(privacy_context, monkeypatch, action):
    home, other, author, peer, foreign = privacy_context
    peer.role = 'ADMIN'
    peer.save()
    report = Report.objects.create(company=home, created_by=author, title='Private incident', description='Test', visibility='PRIVATE', report_type='INCIDENT')
    deliveries = []
    monkeypatch.setattr('reports.views.CommunicationService.send', lambda **kwargs: deliveries.append(kwargs))
    monkeypatch.setattr('reports.views.ActivityAudit.log', lambda **kwargs: None)
    view = ReportViewSet()
    view.request = SimpleNamespace(user=author)
    if action == 'update':
        view.perform_update(SimpleNamespace(save=lambda: report))
    else:
        view.perform_destroy(report)
    assert deliveries == []


@pytest.mark.django_db
def test_critical_report_recipients_keep_authorized_admins(privacy_context):
    home, other, author, peer, foreign = privacy_context
    peer.role = 'ADMIN'
    peer.save()
    report = Report.objects.create(company=home, created_by=author, title='Company incident', description='Test', visibility='COMPANY', report_type='INCIDENT')
    assert ReportViewSet._critical_notification_recipients(report) == [peer]


@pytest.mark.django_db
def test_authorized_deletion_notification_preserves_reference(privacy_context, monkeypatch):
    home, other, author, peer, foreign = privacy_context
    peer.role = 'ADMIN'
    peer.save()
    report = Report.objects.create(company=home, created_by=author, title='Company incident', description='Test', visibility='COMPANY', report_type='INCIDENT')
    reference = str(report.pk)
    deliveries = []
    monkeypatch.setattr('reports.views.CommunicationService.send', lambda **kwargs: deliveries.append(kwargs))
    monkeypatch.setattr('reports.views.ActivityAudit.log', lambda **kwargs: None)
    view = ReportViewSet()
    view.request = SimpleNamespace(user=author)
    view.perform_destroy(report)
    assert len(deliveries) == 1
    assert deliveries[0]['recipient'] == peer
    assert deliveries[0]['reference_id'] == reference
    assert deliveries[0]['url'] == '/reports'
