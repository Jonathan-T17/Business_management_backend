from django.test import TestCase


class CompanyModelTests(TestCase):
    def test_company_exposes_business_configuration_fields(self):
        from .models import Company

        self.assertTrue(hasattr(Company, "timezone"))
        self.assertTrue(hasattr(Company, "default_currency"))
        self.assertTrue(hasattr(Company, "date_format"))
