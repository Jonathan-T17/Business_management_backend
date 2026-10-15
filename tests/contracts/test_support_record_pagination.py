import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from records_management.models import OfficialRecord
from reports.models import Report
from support.models import SupportMessage, SupportTicket


@pytest.mark.django_db
def test_support_pages_preserve_company_labels_and_customer_privacy(django_user_model):
    home = Company.objects.create(name='Support paging home')
    other = Company.objects.create(name='Support paging foreign')
    actor = django_user_model.objects.create_user(email='support-paging@test.local', company=home, role='ADMIN', is_active=True)
    outsider = django_user_model.objects.create_user(email='support-foreign@test.local', company=other, role='ADMIN', is_active=True)
    tickets = [SupportTicket.objects.create(company=home, created_by=actor, subject=f'Ticket {index}', description='Private description') for index in range(26)]
    SupportTicket.objects.create(company=other, created_by=outsider, subject='Foreign ticket', description='Foreign')
    SupportMessage.objects.create(ticket=tickets[0], author=actor, body='Internal only', visibility='INTERNAL')
    client = APIClient()
    client.force_authenticate(actor)
    first = client.get('/api/v1/support/tickets/', {'page_size': 25})
    second = client.get('/api/v1/support/tickets/', {'page_size': 25, 'page': 2})
    assert first.status_code == second.status_code == 200
    assert first.data['count'] == second.data['count'] == 26
    assert len(first.data['results']) == 25 and len(second.data['results']) == 1
    assert first.data['next'] and second.data['previous']
    rows = first.data['results'] + second.data['results']
    assert len({row['id'] for row in rows}) == 26
    assert all(row['company_name'] == home.name for row in rows)
    assert all(not {'messages', 'description', 'context'} & row.keys() for row in rows)
    detail = client.get(f'/api/v1/support/tickets/{tickets[0].pk}/')
    assert detail.data['description'] == 'Private description' and detail.data['messages'] == []


@pytest.mark.django_db
def test_platform_support_filters_before_pagination_and_keeps_company_context(django_user_model):
    company = Company.objects.create(name='Platform support paging')
    actor = django_user_model.objects.create_user(email='support-owner@test.local', company=company, role='EMPLOYEE', is_active=True)
    operator = django_user_model.objects.create_superuser(email='platform-support-paging@test.local', full_name='Synthetic support operator', password='test-only')
    open_ticket = SupportTicket.objects.create(company=company, created_by=actor, subject='Open ticket', description='Open')
    closed_ticket = SupportTicket.objects.create(company=company, created_by=actor, subject='Closed ticket', description='Closed', status='CLOSED')
    SupportMessage.objects.create(ticket=open_ticket, author=operator, body='Operator note', visibility='INTERNAL')
    client = APIClient()
    client.force_authenticate(operator)
    result = client.get('/api/platform/v1/support/tickets/', {'status': 'OPEN'})
    assert result.status_code == 200, result.data
    assert result.data['count'] == 1
    assert result.data['results'][0]['id'] == str(open_ticket.pk)
    assert result.data['results'][0]['company_name'] == company.name
    assert 'messages' not in result.data['results'][0]
    detail = client.get(f'/api/platform/v1/support/tickets/{open_ticket.pk}/')
    assert detail.status_code == 200 and detail.data['messages'][0]['body'] == 'Operator note'
    client.force_authenticate(actor)
    assert client.get('/api/platform/v1/support/tickets/').status_code == 403


@pytest.mark.django_db
def test_official_record_second_page_preserves_visibility(django_user_model):
    home = Company.objects.create(name='Record paging home')
    other = Company.objects.create(name='Record paging foreign')
    actor = django_user_model.objects.create_user(email='record-paging@test.local', company=home, role='EMPLOYEE', is_active=True)
    outsider = django_user_model.objects.create_user(email='record-foreign@test.local', company=other, role='EMPLOYEE', is_active=True)
    content_type = ContentType.objects.get_for_model(Report)
    for index in range(27):
        author, company = (actor, home) if index < 26 else (outsider, other)
        source = Report.objects.create(company=company, created_by=author, title=f'Report {index}', description='Synthetic', visibility='PRIVATE', status='APPROVED')
        OfficialRecord.objects.create(company=company, record_type='REPORT', record_number=f'REC-{index}', title=source.title, content_type=content_type, object_id=str(source.pk), issued_at=timezone.now(), issued_by=author)
    client = APIClient()
    client.force_authenticate(actor)
    first = client.get('/api/v1/official-records/', {'page_size': 25})
    second = client.get('/api/v1/official-records/', {'page_size': 25, 'page': 2})
    assert first.status_code == second.status_code == 200
    assert first.data['count'] == 26 and second.data['count'] == 26
    rows = first.data['results'] + second.data['results']
    assert len(rows) == len({row['id'] for row in rows}) == 26
    assert all(row['record_number'] != 'REC-26' for row in rows)
