import pytest
from django.apps import apps
from django.db import models

@pytest.mark.django_db
def test_employee_id_is_company_scoped_not_globally_unique():
    EmployeeProfile = apps.get_model('organizations', 'EmployeeProfile')
    field = EmployeeProfile._meta.get_field('employee_id')
    assert not field.unique
    constraint_fields = {
        tuple(c.fields) for c in EmployeeProfile._meta.constraints
        if isinstance(c, models.UniqueConstraint)
    }
    assert ('company', 'employee_id') in constraint_fields

@pytest.mark.django_db
def test_company_invite_has_pending_uniqueness_constraint():
    CompanyInvite = apps.get_model('companies', 'CompanyInvite')
    names = {c.name for c in CompanyInvite._meta.constraints}
    assert any('invite' in name.lower() for name in names)
