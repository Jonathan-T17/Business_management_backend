from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PlatformSupportTicketViewSet, SupportTicketViewSet

router = DefaultRouter()
router.register("support/tickets", SupportTicketViewSet, basename="support-tickets")
router.register("platform/support/tickets", PlatformSupportTicketViewSet, basename="platform-support-tickets")

urlpatterns = router.urls
