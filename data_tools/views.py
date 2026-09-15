from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .search import GlobalSearchService
from .serializers import SearchResultSerializer, ImportJobStatusSerializer
from rest_framework.generics import get_object_or_404
from .models import DataExportLog, ImportJob
from .bulk import BulkTaskService
from .exporters import CSVExportService
from .importers import EmployeeImportService
from requests_app.models import BusinessRequest
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.visibility import VisibilityService


class GlobalSearchView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		query = request.query_params.get("q", "").strip()
		if len(query) < 2:
			raise ValidationError({
				"q": "Search requires at least 2 characters."
			})

		results = GlobalSearchService.search(
			user=request.user,
			query=query,
			limit=request.query_params.get("limit"),
		)
		return Response(SearchResultSerializer(results, many=True).data)


class BulkTaskStatusView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		if not CapabilityService.has(request.user, Capabilities.BULK_MANAGE_TASKS):
			raise PermissionDenied("You cannot bulk manage tasks.")
		count = BulkTaskService.change_status(
			user=request.user,
			task_ids=request.data.get("ids", []),
			status=request.data.get("status"),
		)
		return Response({"updated": count})


class EmployeeImportView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		if not CapabilityService.has(request.user, Capabilities.IMPORT_EMPLOYEES):
			raise PermissionDenied("You cannot import employees.")
		upload = request.FILES.get("file")
		if not upload or not upload.name.lower().endswith((".csv", ".xlsx")):
			raise ValidationError("Only CSV and XLSX imports are supported.")
		if upload.size > 10 * 1024 * 1024:
			raise ValidationError("Imports must be 10 MB or smaller.")
		job = ImportJob.objects.create(
			company=request.user.company,
			import_type="EMPLOYEES",
			original_filename=upload.name,
			file=upload,
			created_by=request.user,
		)
		try:
			EmployeeImportService.validate_job(job=job)
		except Exception as exc:
			job.status = "FAILED"
			job.save(update_fields=["status"])
			if isinstance(exc, ValidationError):
				raise
			raise ValidationError("The file could not be read. Check its format and upload again.") from exc
		return Response(ImportJobStatusSerializer(job).data)


class EmployeeImportCommitView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		if not CapabilityService.has(request.user, Capabilities.IMPORT_EMPLOYEES):
			raise PermissionDenied("You cannot import employees.")
		job = get_object_or_404(ImportJob, pk=pk, company=request.user.company)
		EmployeeImportService.commit(job=job, actor=request.user, request=request)
		job.refresh_from_db()
		return Response(ImportJobStatusSerializer(job).data)

class EmployeeImportStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        if not CapabilityService.has(request.user, Capabilities.IMPORT_EMPLOYEES):
            raise PermissionDenied("You cannot inspect employee imports.")
        job = get_object_or_404(ImportJob, pk=pk, company=request.user.company, import_type="EMPLOYEES")
        return Response(ImportJobStatusSerializer(job).data)



class RequestCSVExportView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		if not CapabilityService.has(request.user, Capabilities.EXPORT_OPERATIONAL_DATA):
			raise PermissionDenied("You cannot export operational data.")
		purpose = request.query_params.get("purpose", "").strip()
		if not purpose or len(purpose) > 1000:
			raise ValidationError({"purpose": "Provide an export purpose of up to 1,000 characters."})
		queryset = VisibilityService.business_requests_queryset(
			user=request.user,
			queryset=BusinessRequest.objects.select_related(
				"requester", "branch", "department",
			),
		)
		rows = ((
			item.request_number,
			item.request_type,
			item.title,
			item.status,
			item.priority,
			item.branch.name if item.branch else "",
			item.created_at.isoformat(),
		) for item in queryset)
		response = CSVExportService.response(
			filename="business-requests.csv",
			headers=["Request Number", "Type", "Title", "Status", "Priority", "Branch", "Created"],
			rows=rows,
		)
		DataExportLog.objects.create(
			company=request.user.company,
			export_type="BUSINESS_REQUESTS",
			format="CSV",
			row_count=queryset.count(),
			exported_by=request.user,
			filters={"purpose": purpose},
		)
		return response
