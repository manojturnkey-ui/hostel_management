from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from config.model_mixins import TimeStampedModel
from config.validators import validate_excel_file


class ActiveStatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class CotStatusChoices(models.TextChoices):
    AVAILABLE = "available", "Available"
    PENDING = "pending", "Pending"
    OCCUPIED = "occupied", "Occupied"
    MAINTENANCE = "maintenance", "Maintenance"
    BLOCKED = "blocked", "Blocked"


class BillingCalculationChoices(models.TextChoices):
    INCLUSIVE = "inclusive", "Inclusive"
    EXCLUSIVE_START = "exclusive_start", "Exclusive Start"


class SystemSetting(TimeStampedModel):
    site_title = models.CharField(max_length=150, default="Hostel Management")
    billing_calculation_method = models.CharField(
        max_length=30,
        choices=BillingCalculationChoices.choices,
        default=BillingCalculationChoices.INCLUSIVE,
    )
    payment_window_start_day = models.PositiveSmallIntegerField(default=1)
    payment_window_end_day = models.PositiveSmallIntegerField(default=5)
    grace_period_days = models.PositiveSmallIntegerField(default=5)

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self) -> str:
        return self.site_title

    @classmethod
    def get_solo(cls):
        return cls.objects.order_by("id").first() or cls(site_title="Hostel Management")


class Area(TimeStampedModel):
    area_name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ActiveStatusChoices.choices, default=ActiveStatusChoices.ACTIVE)

    class Meta:
        ordering = ["area_name"]

    def __str__(self) -> str:
        return self.area_name

    def status_badge_class(self) -> str:
        return "success" if self.status == ActiveStatusChoices.ACTIVE else "secondary"


class Building(TimeStampedModel):
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="buildings")
    building_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ActiveStatusChoices.choices, default=ActiveStatusChoices.ACTIVE)

    class Meta:
        ordering = ["area__area_name", "building_name"]
        constraints = [models.UniqueConstraint(fields=["area", "building_name"], name="unique_building_per_area")]

    def __str__(self) -> str:
        return f"{self.building_name} ({self.area.area_name})"

    def status_badge_class(self) -> str:
        return "success" if self.status == ActiveStatusChoices.ACTIVE else "secondary"


class Section(TimeStampedModel):
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name="sections")
    section_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ActiveStatusChoices.choices, default=ActiveStatusChoices.ACTIVE)

    class Meta:
        ordering = ["building__building_name", "section_name"]
        constraints = [models.UniqueConstraint(fields=["building", "section_name"], name="unique_section_per_building")]

    def __str__(self) -> str:
        return f"{self.section_name} ({self.building.building_name})"

    def status_badge_class(self) -> str:
        return "success" if self.status == ActiveStatusChoices.ACTIVE else "secondary"


class Floor(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="floors")
    floor_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ActiveStatusChoices.choices, default=ActiveStatusChoices.ACTIVE)

    class Meta:
        ordering = ["section__section_name", "floor_name"]
        constraints = [models.UniqueConstraint(fields=["section", "floor_name"], name="unique_floor_per_section")]

    def __str__(self) -> str:
        return f"{self.floor_name} ({self.section.section_name})"

    def status_badge_class(self) -> str:
        return "success" if self.status == ActiveStatusChoices.ACTIVE else "secondary"


class Room(TimeStampedModel):
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.CharField(max_length=50)
    room_name = models.CharField(max_length=150, blank=True)
    room_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ActiveStatusChoices.choices, default=ActiveStatusChoices.ACTIVE)

    class Meta:
        ordering = ["floor__floor_name", "room_number"]
        constraints = [models.UniqueConstraint(fields=["floor", "room_number"], name="unique_room_per_floor")]

    def __str__(self) -> str:
        return self.room_name or self.room_number

    def full_label(self) -> str:
        return f"{self.room_number}{' - ' + self.room_name if self.room_name else ''}"

    def status_badge_class(self) -> str:
        return "success" if self.status == ActiveStatusChoices.ACTIVE else "secondary"


class Cot(TimeStampedModel):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="cots")
    cot_number = models.CharField(max_length=50)
    cot_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(max_length=20, choices=CotStatusChoices.choices, default=CotStatusChoices.AVAILABLE)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["room__room_number", "cot_number"]
        constraints = [models.UniqueConstraint(fields=["room", "cot_number"], name="unique_cot_per_room")]

    def __str__(self) -> str:
        return f"{self.room.full_label()} / Cot {self.cot_number}"

    def status_badge_class(self) -> str:
        return {
            CotStatusChoices.AVAILABLE: "success",
            CotStatusChoices.PENDING: "warning",
            CotStatusChoices.OCCUPIED: "danger",
            CotStatusChoices.MAINTENANCE: "secondary",
            CotStatusChoices.BLOCKED: "dark",
        }.get(self.status, "secondary")

    def get_location_path(self) -> str:
        return " / ".join(
            [
                self.room.floor.section.building.area.area_name,
                self.room.floor.section.building.building_name,
                self.room.floor.section.section_name,
                self.room.floor.floor_name,
                self.room.room_number,
                self.cot_number,
            ]
        )

    def current_student_name(self) -> str:
        from apps.bookings.models import Booking, BookingStatusChoices

        active_booking = (
            Booking.objects.filter(cot=self, booking_status=BookingStatusChoices.CONFIRMED)
            .select_related("student")
            .order_by("-confirmed_at", "-created_at")
            .first()
        )
        return active_booking.student.full_name if active_booking else ""

    def public_status_text(self) -> str:
        if self.status == CotStatusChoices.AVAILABLE:
            return "Available"
        if self.status == CotStatusChoices.PENDING:
            return "Payment under verification"
        if self.status == CotStatusChoices.OCCUPIED:
            occupant = self.current_student_name()
            return f"Occupied by: {occupant}" if occupant else "Occupied by guest"
        if self.status == CotStatusChoices.MAINTENANCE:
            return "Under maintenance"
        return "Not available"


class ExcelUploadLog(TimeStampedModel):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
    ]

    uploaded_file = models.FileField(upload_to="excel_uploads/", validators=[validate_excel_file])
    total_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    log_details = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="excel_upload_logs",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Excel Upload #{self.pk}"

    def status_badge_class(self) -> str:
        return {"success": "success", "partial": "warning", "failed": "danger"}.get(self.status, "secondary")
