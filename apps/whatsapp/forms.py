from django import forms

from config.forms import StyledFormMixin

from .models import WhatsAppMessageTemplate, WhatsAppSetting


class BaseWhatsAppModelForm(StyledFormMixin, forms.ModelForm):
    pass


class WhatsAppSettingForm(BaseWhatsAppModelForm):
    class Meta:
        model = WhatsAppSetting
        fields = ["provider", "instance_id", "api_token", "phone_number_id", "access_token", "qr_session_image", "is_active"]


class WhatsAppMessageTemplateForm(BaseWhatsAppModelForm):
    class Meta:
        model = WhatsAppMessageTemplate
        fields = ["template_key", "title", "content", "is_active"]
