from django.urls import path
from rest_framework.routers import DefaultRouter
from users.auth_views import CustomLoginView

from .views import (
    # CustomTokenObtainPairView,
    UserViewSet,
    ProfileViewSet,
    RegisterView,
    VerifyEmailView,
    ResendVerificationView,
    ConfirmPasswordResetView,
    RequestPasswordResetView,
    LogoutView,
    VerifyOTPView,
    DeactivateUserView,
    ActivateUserView,
    ChangeUserRoleView,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    # path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/", CustomLoginView.as_view(), name="token_obtain_pair"),
    path("password-reset/", RequestPasswordResetView.as_view()),
    path("confirm-password-reset/", ConfirmPasswordResetView.as_view()),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("users/<uuid:user_id>/deactivate/", DeactivateUserView.as_view(), name="deactivate-user"),
    path("users/<uuid:user_id>/activate/", ActivateUserView.as_view(), name="activate-user"),
    path("users/<uuid:user_id>/role/", ChangeUserRoleView.as_view(), name="change-user-role"),
]

# Include router URLs as well
urlpatterns += router.urls