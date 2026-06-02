from django.conf import settings
from django.db import models

from config.model_mixins import TimeStampedModel


class DeviceStatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class AccessStatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    BLOCKED = "blocked", "Blocked"


class AccessResultChoices(models.TextChoices):
    ALLOWED = "allowed", "Allowed"
    DENIED = "denied", "Denied"


class BiometricDevice(TimeStampedModel):
    device_name = models.CharField(max_length=150)
    device_code = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    api_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=DeviceStatusChoices.choices, default=DeviceStatusChoices.ACTIVE)

    class Meta:
        ordering = ["device_name"]

    def __str__(self) -> str:
        return f"{self.device_name} ({self.device_code})"


class StudentAccess(TimeStampedModel):
    student = models.ForeignKey("bookings.Student", on_delete=models.PROTECT, related_name="access_records")
    booking = models.OneToOneField("bookings.Booking", on_delete=models.PROTECT, related_name="student_access")
    access_status = models.CharField(max_length=10, choices=AccessStatusChoices.choices, default=AccessStatusChoices.ACTIVE)
    reason = models.TextField(blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student__full_name"]

    def __str__(self) -> str:
        return f"{self.student.full_name} - {self.access_status}"

    def status_badge_class(self) -> str:
        return {
            AccessStatusChoices.ACTIVE: "success",
            AccessStatusChoices.INACTIVE: "secondary",
            AccessStatusChoices.BLOCKED: "danger",
        }.get(self.access_status, "secondary")


class StudentAccessHistory(TimeStampedModel):
    student_access = models.ForeignKey(StudentAccess, on_delete=models.CASCADE, related_name="history")
    previous_status = models.CharField(max_length=10, choices=AccessStatusChoices.choices)
    new_status = models.CharField(max_length=10, choices=AccessStatusChoices.choices)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="student_access_changes",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.student_access.student.full_name}: {self.previous_status} -> {self.new_status}"


class GateAccessLog(TimeStampedModel):
    student = models.ForeignKey("bookings.Student", on_delete=models.SET_NULL, related_name="gate_logs", null=True, blank=True)
    device = models.ForeignKey(BiometricDevice, on_delete=models.SET_NULL, related_name="gate_logs", null=True, blank=True)
    access_time = models.DateTimeField()
    access_result = models.CharField(max_length=10, choices=AccessResultChoices.choices)
    reason = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)

    class Meta:
        ordering = ["-access_time"]

    def __str__(self) -> str:
        return f"{self.student or 'Unknown'} - {self.access_result}"
