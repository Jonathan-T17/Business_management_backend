from rest_framework.routers import DefaultRouter

from .views import (
    FormTemplateViewSet,
    FormSubmissionViewSet,
)


router = DefaultRouter()

router.register(
    "form-templates",
    FormTemplateViewSet,
    basename="form-template",
)

router.register(
    "form-submissions",
    FormSubmissionViewSet,
    basename="form-submission",
)

urlpatterns = router.urls