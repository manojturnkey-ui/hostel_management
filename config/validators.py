from pathlib import Path
import re

from django.core.exceptions import ValidationError


MOBILE_NUMBER_RE = re.compile(r"^[6-9]\d{9}$")
PINCODE_RE = re.compile(r"^\d{6}$")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
EXCEL_EXTENSIONS = {".xlsx", ".xls"}


def validate_mobile_number(value: str) -> None:
    if value and not MOBILE_NUMBER_RE.match(value):
        raise ValidationError("Enter a valid 10-digit mobile number.")


def validate_whatsapp_number(value: str) -> None:
    if value and not MOBILE_NUMBER_RE.match(value):
        raise ValidationError("Enter a valid 10-digit WhatsApp number.")


def validate_pincode(value: str) -> None:
    if value and not PINCODE_RE.match(value):
        raise ValidationError("Enter a valid 6-digit pincode.")


def _validate_extension(uploaded_file, allowed_extensions: set[str], label: str) -> None:
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValidationError(f"{label} must be one of: {allowed}.")


def validate_image_file(uploaded_file) -> None:
    if not uploaded_file:
        return
    _validate_extension(uploaded_file, IMAGE_EXTENSIONS, "Image")
    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValidationError("Image file size must be 5MB or less.")


def validate_excel_file(uploaded_file) -> None:
    if not uploaded_file:
        return
    _validate_extension(uploaded_file, EXCEL_EXTENSIONS, "Excel file")
    if uploaded_file.size > 10 * 1024 * 1024:
        raise ValidationError("Excel file size must be 10MB or less.")
