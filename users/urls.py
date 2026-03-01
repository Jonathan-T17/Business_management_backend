from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = router.urls