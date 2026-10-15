from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from django.db import close_old_connections, connection, connections
from companies.models import Company
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities
from reports.models import Report
from records_management.models import OfficialRecord, RecordSequence
from records_management.services import OfficialRecordService


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_issuance_returns_one_record(django_user_model):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL row-lock behaviour')
    company=Company.objects.create(name='Concurrent issuance')
    actor=django_user_model.objects.create_user(email='parallel-issuer@example.test',company=company,role='EMPLOYEE')
    UserCapabilityGrant.objects.create(company=company,user=actor,capability=Capabilities.ISSUE_OFFICIAL_RECORDS)
    source=Report.objects.create(company=company,created_by=actor,title='Concurrent source',description='Stable snapshot',report_number='CONCURRENT-1')
    start=Barrier(3)
    def issue():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '10s'")
            worker=django_user_model.objects.get(pk=actor.pk)
            report=Report.objects.get(pk=source.pk)
            start.wait(timeout=10)
            return str(OfficialRecordService.issue(source=report,record_type='REPORT',title=report.title,snapshot={'answer':'same'},approval_snapshot=[],actor=worker).pk)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(issue);second=pool.submit(issue)
        start.wait(timeout=10)
        assert first.result(timeout=20)==second.result(timeout=20)
    assert OfficialRecord.objects.filter(company=company).count()==1
    assert RecordSequence.objects.get(company=company,prefix='RPT').last_number==1
