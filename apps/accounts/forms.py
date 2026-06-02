from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError

from config.forms import StyledFormMixin


class PanelAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Email or Username", max_length=150)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser):
            raise ValidationError("This account is not allowed to access the admin panel.", code="invalid_panel_login")


class GuestAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Guest Username", max_length=150)

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff or user.is_superuser or not hasattr(user, "guest_profile"):
            raise ValidationError("Use a valid guest account to sign in here.", code="invalid_guest_login")


class GuestPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    old_password = forms.CharField(label="Current Password", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    new_password1 = forms.CharField(label="New Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    new_password2 = forms.CharField(label="Confirm New Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
