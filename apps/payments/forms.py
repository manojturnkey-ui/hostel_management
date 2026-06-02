from django import forms

from config.forms import StyledFormMixin

from .models import QRCodeSetting


class BasePaymentModelForm(StyledFormMixin, forms.ModelForm):
    pass


class QRCodeSettingForm(BasePaymentModelForm):
    class Meta:
        model = QRCodeSetting
        fields = ["title", "upi_id", "account_name", "qr_image", "is_active"]


class PaymentReviewForm(StyledFormMixin, forms.Form):
    admin_remark = forms.CharField(required=False, widget=forms.Textarea)
