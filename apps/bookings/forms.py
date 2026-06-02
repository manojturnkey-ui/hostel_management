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
            "education",
            "purpose_for_cot_booking",
            "address",
            "city_village",
            "state",
            "pincode",
            "student_photo",
            "address_proof_type",
            "address_proof_front",
            "address_proof_back",
        ]


class PublicBookingForm(StyledFormMixin, forms.Form):
    full_name = forms.CharField(max_length=200)
    mobile_number = forms.CharField(max_length=10, validators=[validate_mobile_number])
    whatsapp_number = forms.CharField(max_length=10, validators=[validate_whatsapp_number])
    relative_contact_number = forms.CharField(max_length=10, required=False, validators=[validate_mobile_number])
    education = forms.CharField(max_length=200, required=False)
    purpose_for_cot_booking = forms.CharField(widget=forms.Textarea)
    address = forms.CharField(widget=forms.Textarea)
    city_village = forms.CharField(max_length=150)
    state = forms.CharField(max_length=150)
    pincode = forms.CharField(max_length=6, validators=[validate_pincode])
    student_photo = forms.ImageField(required=False, validators=[validate_image_file])
    address_proof_type = forms.ChoiceField(choices=AddressProofTypeChoices.choices)
    address_proof_front = forms.ImageField(validators=[validate_image_file])
    address_proof_back = forms.ImageField(required=False, validators=[validate_image_file])
    booking_from_date = forms.DateField(widget=forms.DateInput)
    booking_to_date = forms.DateField(required=False, widget=forms.DateInput)
    utr_transaction_id = forms.CharField(max_length=100)
    payment_screenshot = forms.ImageField(validators=[validate_image_file])

    def clean_booking_from_date(self):
        booking_from_date = self.cleaned_data["booking_from_date"]
        if booking_from_date < timezone.localdate():
            raise forms.ValidationError("Booking start date cannot be in the past.")
        return booking_from_date

    def clean(self):
        cleaned_data = super().clean()
        booking_from_date = cleaned_data.get("booking_from_date")
        booking_to_date = cleaned_data.get("booking_to_date")
        if booking_from_date and booking_to_date and booking_to_date < booking_from_date:
            self.add_error("booking_to_date", "Booking end date cannot be earlier than the start date.")
        return cleaned_data


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
