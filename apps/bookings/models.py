import calendar
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from config.model_mixins import TimeStampedModel
from config.validators import (
    validate_image_file,
    validate_mobile_number,
    validate_pincode,
    validate_whatsapp_number,
)


class AddressProofTypeChoices(models.TextChoices):
    AADHAAR = "aadhaar", "Aadhaar"
    DRIVING_LICENSE = "driving_license", "Driving License"
    OTHER = "other", "Other"


class BookingStatusChoices(models.TextChoices):
    PENDING_ADMIN_CONFIRMATION = "pending_admin_confirmation", "Pending Admin Confirmation"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    VACATED = "vacated", "Vacated"


class BillTypeChoices(models.TextChoices):
    PARTIAL_FIRST_MONTH = "partial_first_month", "Partial First Month"
    REGULAR_MONTHLY = "regular_monthly", "Regular Monthly"
    MANUAL = "manual", "Manual"


class BillPaymentStatusChoices(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PENDING_VERIFICATION = "pending_verification", "Pending Verification"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELLED = "cancelled", "Cancelled"


class Student(TimeStampedModel):
    guest_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="guest_profile",
        blank=True,
        null=True,
    )
    full_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=10, validators=[validate_mobile_number])
    whatsapp_number = models.CharField(max_length=10, validators=[validate_whatsapp_number])
    relative_contact_number = models.CharField(max_length=10, blank=True, validators=[validate_mobile_number])
    education = models.CharField(max_length=200, blank=True)
    purpose_for_cot_booking = models.TextField(blank=True, default="")
    address = models.TextField()
    city_village = models.CharField(max_length=150, blank=True, default="")
    state = models.CharField(max_length=150)
    pincode = models.CharField(max_length=6, validators=[validate_pincode])
    student_photo = models.ImageField(upload_to="students/photos/", validators=[validate_image_file], blank=True, null=True)
    address_proof_type = models.CharField(max_length=20, choices=AddressProofTypeChoices.choices)
    address_proof_front = models.ImageField(upload_to="students/proofs/front/", validators=[validate_image_file])
    address_proof_back = models.ImageField(upload_to="students/proofs/back/", validators=[validate_image_file], blank=True, null=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Guest"
        verbose_name_plural = "Guests"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.mobile_number})"

    @property
    def guest_username(self) -> str:
        return self.guest_user.username if self.guest_user else ""


class Booking(TimeStampedModel):
    ACTIVE_STATUSES = [BookingStatusChoices.PENDING_ADMIN_CONFIRMATION, BookingStatusChoices.CONFIRMED]

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="bookings")
    cot = models.ForeignKey("hostel.Cot", on_delete=models.PROTECT, related_name="bookings")
    booking_from_date = models.DateField()
    booking_to_date = models.DateField(blank=True, null=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    booking_status = models.CharField(
        max_length=30,
        choices=BookingStatusChoices.choices,
        default=BookingStatusChoices.PENDING_ADMIN_CONFIRMATION,
    )
    admin_remark = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_bookings",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.student.full_name} - {self.cot}"

    def clean(self) -> None:
        active_booking_exists = Booking.objects.filter(cot=self.cot, booking_status__in=self.ACTIVE_STATUSES).exclude(pk=self.pk)
        if active_booking_exists.exists():
            raise ValidationError({"cot": "This cot already has an active or pending booking."})

    def status_badge_class(self) -> str:
        return {
            BookingStatusChoices.PENDING_ADMIN_CONFIRMATION: "warning",
            BookingStatusChoices.CONFIRMED: "success",
            BookingStatusChoices.REJECTED: "danger",
            BookingStatusChoices.CANCELLED: "secondary",
            BookingStatusChoices.EXPIRED: "dark",
            BookingStatusChoices.VACATED: "info",
        }.get(self.booking_status, "secondary")

    @property
    def is_active(self) -> bool:
        return self.booking_status == BookingStatusChoices.CONFIRMED and not self.booking_to_date


class MonthlyRentDue(TimeStampedModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="monthly_dues")
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="monthly_dues")
    public_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bill_month = models.PositiveSmallIntegerField()
    bill_year = models.PositiveSmallIntegerField()
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bill_type = models.CharField(max_length=25, choices=BillTypeChoices.choices)
    total_days_in_month = models.PositiveSmallIntegerField(default=0)
    billable_days = models.PositiveSmallIntegerField(default=0)
    due_date = models.DateField()
    grace_period_end_date = models.DateField()
    payment_status = models.CharField(
        max_length=25,
        choices=BillPaymentStatusChoices.choices,
        default=BillPaymentStatusChoices.UNPAID,
    )
    payment_date = models.DateTimeField(blank=True, null=True)
    utr_transaction_id = models.CharField(max_length=100, blank=True)
    payment_screenshot = models.ImageField(
        upload_to="monthly_rent/screenshots/",
        validators=[validate_image_file],
        blank=True,
        null=True,
    )
    admin_remark = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_bills",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-bill_year", "-bill_month", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["booking", "bill_year", "bill_month"], name="unique_bill_per_booking_month")]

    def __str__(self) -> str:
        return f"{self.student.full_name} - {calendar.month_name[self.bill_month]} {self.bill_year}"

    def status_badge_class(self) -> str:
        return {
            BillPaymentStatusChoices.UNPAID: "secondary",
            BillPaymentStatusChoices.PENDING_VERIFICATION: "warning",
            BillPaymentStatusChoices.PAID: "success",
            BillPaymentStatusChoices.OVERDUE: "danger",
            BillPaymentStatusChoices.CANCELLED: "dark",
        }.get(self.payment_status, "secondary")

    @property
    def balance_amount(self) -> Decimal:
        return Decimal("0.00") if self.payment_status == BillPaymentStatusChoices.PAID else self.bill_amount
