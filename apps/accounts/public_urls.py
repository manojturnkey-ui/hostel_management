from django.urls import path

from .views import GuestDashboardView, GuestLoginView, GuestLogoutView, GuestPasswordChangeView


urlpatterns = [
    path("guest/login/", GuestLoginView.as_view(), name="guest_login"),
    path("guest/dashboard/", GuestDashboardView.as_view(), name="guest_dashboard"),
    path("guest/change-password/", GuestPasswordChangeView.as_view(), name="guest_change_password"),
    path("guest/logout/", GuestLogoutView.as_view(), name="guest_logout"),
]
