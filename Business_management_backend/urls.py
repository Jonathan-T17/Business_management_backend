from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from users.views import ActiveCompanyTokenRefreshView
from users.auth_views import CustomLoginView
from core.views import DashboardView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

API_PREFIX = "api/v1/"

urlpatterns = [
    # =========================================================
    # INTERNAL DJANGO ADMIN
    # =========================================================
    path("internal/admin/", admin.site.urls),

    # =========================================================
    # AUTHENTICATION
    # =========================================================
    path(API_PREFIX + "auth/token/", CustomLoginView.as_view(), name="token-obtain"),
    path(API_PREFIX + "auth/token/refresh/", ActiveCompanyTokenRefreshView.as_view(), name="token-refresh"),

    # =========================================================
    # TENANT DASHBOARD
    # =========================================================
    path(API_PREFIX + "dashboard/", DashboardView.as_view(), name="dashboard"),

    # =========================================================
    # IDENTITY / COMPANY
    # =========================================================
    path(API_PREFIX, include("users.urls")),
    path(API_PREFIX, include("companies.urls")),
    path(API_PREFIX + "company-setup/", include("company_setup.urls")),
    path(API_PREFIX + "organizations/", include("organizations.urls")),

    # =========================================================
    # PROJECTS / TASKS / COMMENTS
    # =========================================================
    path(API_PREFIX, include("projects.urls")),
    path(API_PREFIX, include("tasks.urls")),
    path(API_PREFIX, include("comments.urls")),

    # =========================================================
    # REPORTING / WORKFLOWS
    # =========================================================
    path(API_PREFIX, include("reports.urls")),
    path(API_PREFIX, include("workflows.urls")),
    path(API_PREFIX, include("forms_engine.urls")),
    path(API_PREFIX, include("reporting_schedules.urls")),

    # =========================================================
    # BUSINESS OPERATIONS
    # =========================================================
    path(API_PREFIX, include("planning.urls")),
    path(API_PREFIX, include("requests_app.urls")),
    path(API_PREFIX, include("field_operations.urls")),

    # =========================================================
    # DOCUMENTS / RECORDS
    # =========================================================
    path(API_PREFIX, include("documents.urls")),
    path(API_PREFIX, include("records_management.urls")),

    # =========================================================
    # ACTIVITY / NOTIFICATIONS
    # =========================================================
    path(API_PREFIX, include("activity.urls")),
    path(API_PREFIX, include("notifications.urls")),

    # =========================================================
    # ANALYTICS / AI
    # =========================================================
    path(API_PREFIX + "analytics/", include("analytics_ai.urls")),

    # =========================================================
    # CHAT
    # =========================================================
    path(API_PREFIX + "chat/", include("chat.urls")),

    # =========================================================
    # SUBSCRIPTIONS / SECURITY
    # =========================================================
    path(API_PREFIX, include("subscriptions.urls")),
    path(API_PREFIX, include("security.urls")),

    # =========================================================
    # DATA TOOLS / SUPPORT
    # =========================================================
    path(API_PREFIX, include("data_tools.urls")),
    path(API_PREFIX, include("support.urls")),

    # =========================================================
    # PLATFORM CONTROL CENTER
    # =========================================================
    path("api/platform/v1/", include("platform_admin.urls")),
]

# =============================================================
# DEVELOPMENT API DOCUMENTATION
# =============================================================
if settings.DEBUG:
    urlpatterns += [
        path(API_PREFIX + "schema/", SpectacularAPIView.as_view(), name="schema"),
        path(API_PREFIX + "docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
