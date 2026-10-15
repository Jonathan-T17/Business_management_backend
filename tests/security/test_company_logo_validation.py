from io import BytesIO
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from companies.serializers import CompanySerializer


def logo(format='PNG', dimensions=(32, 32)):
    data = BytesIO()
    Image.new('RGB', dimensions).save(data, format=format)
    return SimpleUploadedFile('logo.' + format.lower(), data.getvalue())


@pytest.mark.parametrize('format', ['PNG', 'JPEG', 'WEBP'])
def test_company_logo_accepts_verified_images(format):
    serializer = CompanySerializer()
    image = serializer.fields['logo'].run_validation(logo(format))
    assert serializer.validate_logo(image) is image
    assert serializer.validate_logo(None) is None


def test_company_logo_rejects_other_formats_oversized_images_and_fake_images():
    serializer = CompanySerializer()
    with pytest.raises((ValidationError, DjangoValidationError)):
        serializer.fields['logo'].run_validation(SimpleUploadedFile('fake.png', b'<svg>not a raster image</svg>', content_type='image/png'))
    for image in [logo('GIF'), logo(dimensions=(4097, 1))]:
        with pytest.raises(ValidationError):
            serializer.validate_logo(serializer.fields['logo'].run_validation(image))
    image = serializer.fields['logo'].run_validation(logo())
    image.size = 2 * 1024 * 1024 + 1
    with pytest.raises(ValidationError):
        serializer.validate_logo(image)


@pytest.mark.django_db
def test_logo_upload_and_removal_stay_with_company_admin(django_user_model, tmp_path, settings):
    from rest_framework.test import APIClient
    from companies.models import Company
    settings.MEDIA_ROOT = str(tmp_path)
    company = Company.objects.create(name='Logo company')
    other = Company.objects.create(name='Other logo company')
    admin = django_user_model.objects.create_user(email='logo-admin@example.test', company=company, role='ADMIN')
    employee = django_user_model.objects.create_user(email='logo-employee@example.test', company=company, role='EMPLOYEE')
    client = APIClient()
    client.force_authenticate(employee)
    url = f'/api/v1/company/{company.pk}/'
    assert client.patch(url, {'logo': logo()}, format='multipart').status_code == 403
    client.force_authenticate(admin)
    response = client.patch(url, {'logo': logo()}, format='multipart')
    assert response.status_code == 200, response.data
    assert response.data['logo']
    assert client.patch(f'/api/v1/company/{other.pk}/', {'logo': None}, format='json').status_code == 404
    response = client.patch(url, {'logo': None}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['logo'] is None
