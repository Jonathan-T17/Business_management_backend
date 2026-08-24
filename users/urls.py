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
]

# Include router URLs as well
urlpatterns += router.urls