from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())
        raise PermissionDenied("You do not have permission to access this panel.")


class PanelLoginRequiredMixin(LoginRequiredMixin, StaffRequiredMixin):
    login_url = reverse_lazy("panel_login")


class GuestRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("guest_login")

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and not (user.is_staff or user.is_superuser) and hasattr(user, "guest_profile")

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())
        if self.request.user.is_staff or self.request.user.is_superuser:
            return redirect("panel_dashboard")
        raise PermissionDenied("You do not have permission to access this guest portal.")
