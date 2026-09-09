from django.db import models
from django.conf import settings
import uuid


class ImportJob(models.Model):
	TYPES = (
		("EMPLOYEES", "Employees"),
		("TASKS", "Tasks"),
		("FIELD_STOPS", "Field Stops"),
		("CUSTOM", "Custom"),
	)
	STATUS_CHOICES = (
		("UPLOADED", "Uploaded"),
		("VALIDATING", "Validating"),
		("READY", "Ready"),
		("COMPLETED", "Completed"),
		("FAILED", "Failed"),
		("CANCELLED", "Cancelled"),
	)
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="import_jobs")
	import_type = models.CharField(max_length=30, choices=TYPES)
	original_filename = models.CharField(max_length=255)
	file = models.FileField(upload_to="imports/")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="UPLOADED")
	total_rows = models.PositiveIntegerField(default=0)
	valid_rows = models.PositiveIntegerField(default=0)
	invalid_rows = models.PositiveIntegerField(default=0)
	validation_result = models.JSONField(default=dict, blank=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_import_jobs")
	created_at = models.DateTimeField(auto_now_add=True)
	completed_at = models.DateTimeField(null=True, blank=True)


class DataExportLog(models.Model):
	company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="data_export_logs")
	export_type = models.CharField(max_length=50)
	format = models.CharField(max_length=10)
	row_count = models.PositiveIntegerField(default=0)
	exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="data_exports")
	filters = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

# Create your models here.
