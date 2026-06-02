from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from config.model_mixins import TimeStampedModel
from config.validators import validate_image_file


class PaymentMethodChoices(models.TextChoices):
    UPI_QR = "upi_qr", "UPI QR"


class PaymentStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Rejected"


class QRCodeSetting(TimeStampedModel):
    title = models.CharField(max_length=150)
    upi_id = models.CharField(max_length=150, blank=True)
    account_name = models.CharField(max_length=150, blank=True)
    qr_image = models.ImageField(upload_to="qr_codes/", validators=[validate_image_file])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_active", "-created_at"]
        verbose_name = "QR Code Setting"
        verbose_name_plural = "QR Code Settings"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            QRCodeSetting.objects.exclude(pk=self.pk).update(is_active=False)


class Payment(TimeStampedModel):
    booking = models.OneToOneField("bookings.Booking", on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    payment_method = models.CharField(max_length=20, choices=PaymentMethodChoices.choices, default=PaymentMethodChoices.UPI_QR)
    utr_transaction_id = models.CharField(max_length=100)
    payment_screenshot = models.ImageField(upload_to="booking_payments/screenshots/", validators=[validate_image_file])
    payment_status = models.CharField(max_length=15, choices=PaymentStatusChoices.choices, default=PaymentStatusChoices.PENDING)
    admin_remark = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_payments",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payment for {self.booking}"

    def clean(self) -> None:
        if not self.utr_transaction_id:
            raise ValidationError({"utr_transaction_id": "UTR / Transaction ID is required."})
        if not self.payment_screenshot:
            raise ValidationError({"payment_screenshot": "Payment screenshot is required."})

    def status_badge_class(self) -> str:
        return {
            PaymentStatusChoices.PENDING: "warning",
            PaymentStatusChoices.CONFIRMED: "success",
            PaymentStatusChoices.REJECTED: "danger",
        }.get(self.payment_status, "secondary")
