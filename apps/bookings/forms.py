from django import forms
from django.utils import timezone

from config.forms import StyledFormMixin
from config.validators import (
    validate_image_file,
    validate_mobile_number,
    validate_pincode,
    validate_whatsapp_number,
)

from .models import AddressProofTypeChoices, MonthlyRentDue, Student


class BaseBookingModelForm(StyledFormMixin, forms.ModelForm):
    pass


class StudentForm(BaseBookingModelForm):
    class Meta:
        model = Student
        fields = [
            "full_name",
            "mobile_number",
            "whatsapp_number",
            "relative_contact_number",
            "address",
            "state",
            "pincode",
            "student_photo",
            "address_proof_type",
            "address_proof_front",
            "address_proof_back",
        ]


class PublicBookingForm(StyledFormMixin, forms.Form):
    full_name = forms.CharField(max_length=200, label="Guest Full Name")
    mobile_number = forms.CharField(max_length=10, validators=[validate_mobile_number], label="Mobile Number")
    whatsapp_number = forms.CharField(max_length=10, validators=[validate_whatsapp_number], label="WhatsApp Number")
    relative_contact_number = forms.CharField(
        max_length=10,
        required=False,
        validators=[validate_mobile_number],
        label="Relative Contact Number",
    )
    address = forms.CharField(widget=forms.TextInput, label="Address")
    state = forms.CharField(max_length=150, label="State")
    pincode = forms.CharField(max_length=6, validators=[validate_pincode], label="Pincode")
    student_photo = forms.ImageField(required=False, validators=[validate_image_file], label="Guest Photo")
    address_proof_type = forms.ChoiceField(choices=AddressProofTypeChoices.choices, label="Address Proof Type")
    address_proof_front = forms.ImageField(validators=[validate_image_file], label="Address Proof Front")
    address_proof_back = forms.ImageField(required=False, validators=[validate_image_file], label="Address Proof Back")
    booking_from_date = forms.DateField(widget=forms.DateInput, label="Staying Start Date")
    utr_transaction_id = forms.CharField(max_length=100, label="Payment UTR / Transaction ID")
    payment_screenshot = forms.ImageField(validators=[validate_image_file], label="Payment Screenshot")

    def clean_booking_from_date(self):
        booking_from_date = self.cleaned_data["booking_from_date"]
        if booking_from_date < timezone.localdate():
            raise forms.ValidationError("Booking start date cannot be in the past.")
        return booking_from_date


class BookingReviewForm(StyledFormMixin, forms.Form):
    admin_remark = forms.CharField(required=False, widget=forms.Textarea)


class MonthlyRentPaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MonthlyRentDue
        fields = ["utr_transaction_id", "payment_screenshot"]


class ManualBillGenerateForm(StyledFormMixin, forms.Form):
    booking = forms.ModelChoiceField(queryset=None)
    bill_month = forms.IntegerField(min_value=1, max_value=12)
    bill_year = forms.IntegerField(min_value=2000)
    bill_amount = forms.DecimalField(min_value=0, decimal_places=2, max_digits=10)
    billing_period_start = forms.DateField(widget=forms.DateInput)
    billing_period_end = forms.DateField(widget=forms.DateInput)
    due_date = forms.DateField(widget=forms.DateInput)
    grace_period_end_date = forms.DateField(widget=forms.DateInput)
    admin_remark = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        from .models import Booking, BookingStatusChoices

        super().__init__(*args, **kwargs)
        self.fields["booking"].queryset = Booking.objects.filter(booking_status=BookingStatusChoices.CONFIRMED).select_related("student", "cot")


class GraceExtensionForm(StyledFormMixin, forms.Form):
    grace_period_end_date = forms.DateField(widget=forms.DateInput)
    admin_remark = forms.CharField(required=False, widget=forms.Textarea)
