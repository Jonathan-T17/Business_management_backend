from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, BranchViewSet, CompanyInviteViewSet

router = DefaultRouter()
router.register("company", CompanyViewSet, basename="company")
router.register("branches", BranchViewSet, basename="branches")
router.register("invites", CompanyInviteViewSet, basename="invites")

urlpatterns = router.urls