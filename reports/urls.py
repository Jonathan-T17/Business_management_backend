from rest_framework.routers import DefaultRouter
from .views import ReportViewSet
from .views import ReportCommentViewSet

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="reports")
router.register("report-comments", ReportCommentViewSet, basename="report-comments")

urlpatterns = router.urls