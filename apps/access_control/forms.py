from django import forms

from config.forms import StyledFormMixin

from .models import BiometricDevice, StudentAccess


class BaseAccessModelForm(StyledFormMixin, forms.ModelForm):
    pass


class BiometricDeviceForm(BaseAccessModelForm):
    class Meta:
        model = BiometricDevice
        fields = ["device_name", "device_code", "location", "ip_address", "api_url", "status"]


class StudentAccessForm(BaseAccessModelForm):
    class Meta:
        model = StudentAccess
        fields = ["access_status", "reason", "valid_from", "valid_to"]
