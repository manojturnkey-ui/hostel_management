from django.db import models

from config.model_mixins import TimeStampedModel
from config.validators import validate_image_file


class WhatsAppProviderChoices(models.TextChoices):
    GREEN_API = "green_api", "Green API"
    WHATSAPP_CLOUD_API = "whatsapp_cloud_api", "WhatsApp Cloud API"
    MANUAL_PLACEHOLDER = "manual_placeholder", "Manual Placeholder"


class WhatsAppLogStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class WhatsAppSetting(TimeStampedModel):
    provider = models.CharField(
        max_length=30,
        choices=WhatsAppProviderChoices.choices,
        default=WhatsAppProviderChoices.MANUAL_PLACEHOLDER,
    )
    instance_id = models.CharField(max_length=150, blank=True)
    api_token = models.CharField(max_length=255, blank=True)
    phone_number_id = models.CharField(max_length=150, blank=True)
    access_token = models.CharField(max_length=255, blank=True)
    qr_session_image = models.ImageField(
        upload_to="whatsapp/session_qr/",
        validators=[validate_image_file],
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_active", "-created_at"]

    def __str__(self) -> str:
        return self.get_provider_display()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            WhatsAppSetting.objects.exclude(pk=self.pk).update(is_active=False)


class WhatsAppMessageTemplate(TimeStampedModel):
    template_key = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=150)
    content = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["template_key"]

    def __str__(self) -> str:
        return self.template_key


class WhatsAppLog(TimeStampedModel):
    student = models.ForeignKey("bookings.Student", on_delete=models.SET_NULL, related_name="whatsapp_logs", null=True, blank=True)
    mobile_number = models.CharField(max_length=20)
    event_type = models.CharField(max_length=50)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=WhatsAppLogStatusChoices.choices, default=WhatsAppLogStatusChoices.PENDING)
    response = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} - {self.mobile_number}"
