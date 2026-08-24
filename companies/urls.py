from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyViewSet,
    BranchViewSet,
    CompanyInviteViewSet,
    InvitationInfoView,
    AcceptInvitationView,
)


router = DefaultRouter()

router.register(
    "company",
    CompanyViewSet,
    basename="company",
)

router.register(
    "branches",
    BranchViewSet,
    basename="branches",
)

router.register(
    "invites",
    CompanyInviteViewSet,
    basename="invites",
)


urlpatterns = [
    path(
        "invite/<uuid:token>/",
        InvitationInfoView.as_view(),
        name="invitation-info",
    ),

    path(
        "invite/<uuid:token>/accept/",
        AcceptInvitationView.as_view(),
        name="invitation-accept",
    ),
]

urlpatterns += router.urls