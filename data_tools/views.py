from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .search import GlobalSearchService
from .serializers import SearchResultSerializer
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
		job = ImportJob.objects.create(
			company=request.user.company,
			import_type="EMPLOYEES",
			original_filename=upload.name,
			file=upload,
			created_by=request.user,
		)
		result = EmployeeImportService.validate_job(job=job)
		return Response({"job_id": str(job.id), **result})


class EmployeeImportCommitView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, pk):
		if not CapabilityService.has(request.user, Capabilities.IMPORT_EMPLOYEES):
			raise PermissionDenied("You cannot import employees.")
		job = ImportJob.objects.get(pk=pk, company=request.user.company)
		return Response({
			"created": EmployeeImportService.commit(
				job=job,
				actor=request.user,
				request=request,
			)
		})


class RequestCSVExportView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		if not CapabilityService.has(request.user, Capabilities.EXPORT_OPERATIONAL_DATA):
			raise PermissionDenied("You cannot export operational data.")
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
			item.requester.email if item.requester else "",
			item.branch.name if item.branch else "",
			item.created_at.isoformat(),
		) for item in queryset)
		response = CSVExportService.response(
			filename="business-requests.csv",
			headers=["Request Number", "Type", "Title", "Status", "Priority", "Requester", "Branch", "Created"],
			rows=rows,
		)
		DataExportLog.objects.create(
			company=request.user.company,
			export_type="BUSINESS_REQUESTS",
			format="CSV",
			row_count=queryset.count(),
			exported_by=request.user,
		)
		return response
