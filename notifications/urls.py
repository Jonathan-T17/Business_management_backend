from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import NotificationPreferenceView, NotificationViewSet


router = DefaultRouter()

router.register(
    "notifications",
    NotificationViewSet,
    basename="notifications",
)

urlpatterns = [
    path(
        "notification-preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
]

urlpatterns += router.urls
