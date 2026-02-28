from rest_framework.routers import DefaultRouter
from .views import ReportViewSet

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="reports")

urlpatterns = router.urls