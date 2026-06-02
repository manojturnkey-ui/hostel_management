from django import forms
from django.contrib.auth.forms import AuthenticationForm

from config.forms import StyledFormMixin


class PanelAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Email or Username", max_length=150)
