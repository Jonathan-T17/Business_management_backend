from django.urls import path

from .views import (
    GlobalSearchView,
    BulkTaskStatusView,
    EmployeeImportView,
    EmployeeImportCommitView,
    RequestCSVExportView,
)


urlpatterns = [
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("bulk/tasks/status/", BulkTaskStatusView.as_view(), name="bulk-task-status"),
    path("imports/employees/", EmployeeImportView.as_view(), name="employee-import"),
    path("imports/employees/<uuid:pk>/commit/", EmployeeImportCommitView.as_view(), name="employee-import-commit"),
    path("exports/business-requests.csv", RequestCSVExportView.as_view(), name="business-request-export"),
]