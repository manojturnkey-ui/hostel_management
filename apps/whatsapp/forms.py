from django import forms

from config.forms import StyledFormMixin

from .models import WhatsAppMessageTemplate, WhatsAppSetting


class BaseWhatsAppModelForm(StyledFormMixin, forms.ModelForm):
    pass


class WhatsAppSettingForm(BaseWhatsAppModelForm):
    class Meta:
        model = WhatsAppSetting
        fields = ["service_name", "service_url", "api_key", "default_country_code", "session_name", "is_active"]
        widgets = {
            "api_key": forms.PasswordInput(render_value=True),
        }

    def clean_service_url(self):
        service_url = (self.cleaned_data.get("service_url") or "").strip()
        return service_url.rstrip("/")


class WhatsAppMessageTemplateForm(BaseWhatsAppModelForm):
    class Meta:
        model = WhatsAppMessageTemplate
        fields = ["template_key", "title", "content", "is_active"]
