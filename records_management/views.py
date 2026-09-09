from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.visibility import VisibilityService

from .models import OfficialRecord, RecordExport
from .serializers import OfficialRecordDetailSerializer, OfficialRecordSerializer
from .services import OfficialRecordPDFService, OfficialRecordService


class OfficialRecordViewSet(viewsets.ReadOnlyModelViewSet):
	permission_classes = [IsAuthenticated]

	def get_serializer_class(self):
		return (
			OfficialRecordDetailSerializer
			if self.action == "retrieve"
			else OfficialRecordSerializer
		)

	def get_queryset(self):
		queryset = OfficialRecord.objects.select_related(
			"company", "branch", "issued_by", "content_type", "supersedes",
		)
		return VisibilityService.official_records_queryset(
			user=self.request.user,
			queryset=queryset,
		)

	@action(detail=True, methods=["get"], url_path="pdf")
	def pdf(self, request, pk=None):
		record = self.get_object()
		if not CapabilityService.has(
			request.user,
			Capabilities.EXPORT_OFFICIAL_RECORDS,
		):
			raise PermissionDenied("You cannot export official records.")

		RecordExport.objects.create(
			company=record.company,
			record=record,
			export_format="PDF",
			exported_by=request.user,
			purpose=request.query_params.get("purpose", ""),
		)
		return FileResponse(
			OfficialRecordPDFService.render(record=record),
			as_attachment=True,
			filename=f"{record.record_number}.pdf",
			content_type="application/pdf",
		)

	@action(detail=True, methods=["post"], url_path="void")
	def void(self, request, pk=None):
		record = self.get_object()
		if not CapabilityService.has(
			request.user,
			Capabilities.VOID_OFFICIAL_RECORDS,
		):
			raise PermissionDenied("You cannot void official records.")

		OfficialRecordService.void(
			record=record,
			actor=request.user,
			reason=request.data.get("reason", ""),
			request=request,
		)
		return Response(
			OfficialRecordDetailSerializer(
				record,
				context={"request": request},
			).data
		)


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_record(request, token):
	record = get_object_or_404(OfficialRecord, verification_token=token)
	return Response({
		"valid": record.status == "ACTIVE",
		"record_number": record.record_number,
		"company": record.company.name,
		"record_type": record.record_type,
		"issued_at": record.issued_at,
		"status": record.status,
	})
