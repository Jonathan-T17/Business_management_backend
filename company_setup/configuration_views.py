from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.capabilities import Capabilities
from security.services import create_audit_log
from documents.models import DocumentCategory
from documents.serializers import DocumentCategorySerializer
from .permissions import IsCompanySetupAdmin
from .models import RolePreset, RequestTypeDefinition, FieldActivityTemplate, OfficialRecordPolicy, NotificationPolicy
from .serializers import RolePresetSerializer, RequestTypeDefinitionSerializer, FieldActivityTemplateSerializer, OfficialRecordPolicySerializer, NotificationPolicySerializer
from .services import RolePresetService


class CompanyConfigurationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.company).order_by('pk')

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self.audit(instance, 'CREATE')

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self.audit(instance, 'UPDATE')

    def audit(self, instance, operation):
        create_audit_log(user=self.request.user, company=self.request.user.company,
                         request=self.request, action=operation, obj=instance,
                         description=f'Company configuration {operation.lower()}: {type(instance).__name__}.')


class RolePresetViewSet(CompanyConfigurationViewSet):
    queryset = RolePreset.objects.all()
    serializer_class = RolePresetSerializer

    def get_queryset(self):
        return self.queryset.filter(Q(company=self.request.user.company) | Q(company__isnull=True, is_system=True)).order_by('name')

    def save_preset(self, serializer):
        serializer.instance = RolePresetService.save(company=self.request.user.company, actor=self.request.user,
            data=serializer.validated_data, instance=serializer.instance, request=self.request)

    def perform_create(self, serializer):
        self.save_preset(serializer)

    def perform_update(self, serializer):
        self.save_preset(serializer)


class ActivatableConfigurationViewSet(CompanyConfigurationViewSet):
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        return self.set_active(True)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        return self.set_active(False)

    @transaction.atomic
    def set_active(self, active):
        instance = self.get_object()
        instance.is_active = active
        instance.save(update_fields=['is_active'])
        self.audit(instance, 'UPDATE')
        return Response(self.get_serializer(instance).data)


class RequestTypeViewSet(ActivatableConfigurationViewSet):
    queryset = RequestTypeDefinition.objects.all()
    serializer_class = RequestTypeDefinitionSerializer


class FieldTemplateViewSet(ActivatableConfigurationViewSet):
    queryset = FieldActivityTemplate.objects.all()
    serializer_class = FieldActivityTemplateSerializer


class DocumentCategoryViewSet(CompanyConfigurationViewSet):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer


class RecordPolicyViewSet(CompanyConfigurationViewSet):
    queryset = OfficialRecordPolicy.objects.all()
    serializer_class = OfficialRecordPolicySerializer


class NotificationPolicyViewSet(CompanyConfigurationViewSet):
    queryset = NotificationPolicy.objects.all()
    serializer_class = NotificationPolicySerializer

from rest_framework.views import APIView

class SetupCapabilitiesView(APIView):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get(self, request):
        return Response([item for item in Capabilities.catalogue() if item['tenant_assignable']])
