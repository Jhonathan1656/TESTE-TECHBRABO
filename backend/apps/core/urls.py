from django.urls import path

from apps.core.views import CurrentUserView, HealthView, LoginView, LogoutView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", CurrentUserView.as_view(), name="auth-me"),
]
