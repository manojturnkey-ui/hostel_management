from __future__ import annotations

from dataclasses import dataclass
from string import Formatter

from .models import (
    WhatsAppLog,
    WhatsAppLogStatusChoices,
    WhatsAppMessageTemplate,
    WhatsAppProviderChoices,
    WhatsAppSetting,
)


DEFAULT_TEMPLATES = {
    "booking_submitted": "Dear {student_name}, your cot booking request for cot {cot_number} in room {room_number} has been submitted.",
    "payment_pending": "Dear {student_name}, your payment is under verification. UTR: {utr}.",
    "booking_confirmed": "Dear {student_name}, your booking for cot {cot_number} in room {room_number}, {building_name} is confirmed.",
    "booking_rejected": "Dear {student_name}, your booking request is rejected. Remark: {admin_remark}.",
    "monthly_rent_due": "Dear {student_name}, your hostel rent bill for {bill_month} is Rs. {amount}. Please pay before {grace_period_end_date}.",
    "first_bill_generated": "Dear {student_name}, your first hostel bill for {bill_month} is Rs. {amount}. Please pay before {grace_period_end_date}.",
    "monthly_bill_generated": "Dear {student_name}, your hostel rent bill for {bill_month} is Rs. {amount}. Please pay before {grace_period_end_date}.",
    "payment_reminder": "Dear {student_name}, your hostel rent payment of Rs. {amount} is pending. Please pay before {grace_period_end_date} to keep your gate access active.",
    "grace_period_ending_reminder": "Dear {student_name}, your rent grace period ends on {grace_period_end_date}. Please pay Rs. {amount} to avoid access blocking.",
    "payment_received": "Dear {student_name}, your payment of Rs. {amount} is received. UTR: {utr}.",
    "access_blocked": "Dear {student_name}, your hostel gate access is blocked due to unpaid rent for {bill_month}. Please contact admin.",
    "access_active": "Dear {student_name}, your payment is confirmed and gate access is active.",
}


def ensure_default_templates() -> None:
    for template_key, content in DEFAULT_TEMPLATES.items():
        WhatsAppMessageTemplate.objects.get_or_create(
            template_key=template_key,
            defaults={"title": template_key.replace("_", " ").title(), "content": content, "is_active": True},
        )


@dataclass
class ProviderResponse:
    status: str
    response: str


class BaseWhatsAppProvider:
    def __init__(self, setting: WhatsAppSetting | None):
        self.setting = setting

    def send_message(self, mobile_number: str, message: str) -> ProviderResponse:
        raise NotImplementedError


class ManualPlaceholderProvider(BaseWhatsAppProvider):
    def send_message(self, mobile_number: str, message: str) -> ProviderResponse:
        return ProviderResponse(
            status=WhatsAppLogStatusChoices.PENDING,
            response="Manual placeholder active. Message saved for later sending.",
        )


class GreenAPIProvider(BaseWhatsAppProvider):
    def send_message(self, mobile_number: str, message: str) -> ProviderResponse:
        if not self.setting or not self.setting.instance_id or not self.setting.api_token:
            return ProviderResponse(
                status=WhatsAppLogStatusChoices.FAILED,
                response="Green API credentials are missing. Message stored only in log.",
            )
        return ProviderResponse(
            status=WhatsAppLogStatusChoices.PENDING,
            response="Green API integration stub is ready. Real sending will be added later.",
        )


class WhatsAppCloudAPIProvider(BaseWhatsAppProvider):
    def send_message(self, mobile_number: str, message: str) -> ProviderResponse:
        if not self.setting or not self.setting.phone_number_id or not self.setting.access_token:
            return ProviderResponse(
                status=WhatsAppLogStatusChoices.FAILED,
                response="WhatsApp Cloud API credentials are missing. Message stored only in log.",
            )
        return ProviderResponse(
            status=WhatsAppLogStatusChoices.PENDING,
            response="WhatsApp Cloud API integration stub is ready. Real sending will be added later.",
        )


def get_provider(setting: WhatsAppSetting | None) -> BaseWhatsAppProvider:
    provider_map = {
        WhatsAppProviderChoices.GREEN_API: GreenAPIProvider,
        WhatsAppProviderChoices.WHATSAPP_CLOUD_API: WhatsAppCloudAPIProvider,
        WhatsAppProviderChoices.MANUAL_PLACEHOLDER: ManualPlaceholderProvider,
    }
    provider_class = provider_map.get(setting.provider if setting else WhatsAppProviderChoices.MANUAL_PLACEHOLDER, ManualPlaceholderProvider)
    return provider_class(setting)


def get_template_content(template_key: str) -> str:
    ensure_default_templates()
    template = WhatsAppMessageTemplate.objects.filter(template_key=template_key, is_active=True).first()
    return template.content if template else DEFAULT_TEMPLATES.get(template_key, "")


def render_template(template_key: str, context: dict) -> str:
    raw_template = get_template_content(template_key)
    safe_context = {key: value or "" for key, value in context.items()}
    for _, field_name, _, _ in Formatter().parse(raw_template):
        if field_name:
            safe_context.setdefault(field_name, "")
    return raw_template.format(**safe_context)


def log_and_send(template_key: str, student, mobile_number: str, event_type: str, context: dict) -> WhatsAppLog:
    message = render_template(template_key, context)
    setting = WhatsAppSetting.objects.filter(is_active=True).order_by("-created_at").first()
    provider = get_provider(setting)
    provider_response = provider.send_message(mobile_number, message)
    return WhatsAppLog.objects.create(
        student=student,
        mobile_number=mobile_number,
        event_type=event_type,
        message=message,
        status=provider_response.status,
        response=provider_response.response,
    )


def booking_context(booking) -> dict:
    return {
        "student_name": booking.student.full_name,
        "cot_number": booking.cot.cot_number,
        "room_number": booking.cot.room.room_number,
        "building_name": booking.cot.room.floor.section.building.building_name,
        "amount": booking.total_amount,
        "utr": getattr(booking.payment, "utr_transaction_id", ""),
        "booking_from_date": booking.booking_from_date,
        "admin_remark": booking.admin_remark,
    }


def bill_context(bill) -> dict:
    return {
        "student_name": bill.student.full_name,
        "cot_number": bill.booking.cot.cot_number,
        "room_number": bill.booking.cot.room.room_number,
        "building_name": bill.booking.cot.room.floor.section.building.building_name,
        "amount": bill.bill_amount,
        "utr": bill.utr_transaction_id,
        "bill_month": f"{bill.bill_month}/{bill.bill_year}",
        "grace_period_end_date": bill.grace_period_end_date,
        "admin_remark": bill.admin_remark,
    }


def send_booking_submitted_message(booking):
    return log_and_send("booking_submitted", booking.student, booking.student.whatsapp_number, "booking_submitted", booking_context(booking))


def send_payment_pending_message(booking):
    return log_and_send("payment_pending", booking.student, booking.student.whatsapp_number, "payment_pending", booking_context(booking))


def send_booking_confirmed_message(booking):
    return log_and_send("booking_confirmed", booking.student, booking.student.whatsapp_number, "booking_confirmed", booking_context(booking))


def send_booking_rejected_message(booking):
    return log_and_send("booking_rejected", booking.student, booking.student.whatsapp_number, "booking_rejected", booking_context(booking))


def send_payment_received_message(payment_or_bill):
    if hasattr(payment_or_bill, "booking"):
        if hasattr(payment_or_bill, "bill_amount"):
            context = bill_context(payment_or_bill)
            student = payment_or_bill.student
            mobile_number = payment_or_bill.student.whatsapp_number
        else:
            context = booking_context(payment_or_bill.booking)
            context["amount"] = payment_or_bill.amount
            context["utr"] = payment_or_bill.utr_transaction_id
            student = payment_or_bill.booking.student
            mobile_number = payment_or_bill.booking.student.whatsapp_number
        return log_and_send("payment_received", student, mobile_number, "payment_received", context)
    return None


def send_monthly_bill_generated_message(bill):
    return log_and_send("monthly_bill_generated", bill.student, bill.student.whatsapp_number, "monthly_bill_generated", bill_context(bill))


def send_first_bill_generated_message(bill):
    return log_and_send("first_bill_generated", bill.student, bill.student.whatsapp_number, "first_bill_generated", bill_context(bill))


def send_monthly_rent_due_message(bill):
    return log_and_send("monthly_rent_due", bill.student, bill.student.whatsapp_number, "monthly_rent_due", bill_context(bill))


def send_payment_reminder_message(bill):
    return log_and_send("payment_reminder", bill.student, bill.student.whatsapp_number, "payment_reminder", bill_context(bill))


def send_grace_period_ending_reminder_message(bill):
    return log_and_send(
        "grace_period_ending_reminder",
        bill.student,
        bill.student.whatsapp_number,
        "grace_period_ending_reminder",
        bill_context(bill),
    )


def send_access_blocked_message(bill):
    return log_and_send("access_blocked", bill.student, bill.student.whatsapp_number, "access_blocked", bill_context(bill))


def send_access_active_message(student_access, bill=None):
    context = bill_context(bill) if bill else {
        "student_name": student_access.student.full_name,
        "cot_number": student_access.booking.cot.cot_number,
        "room_number": student_access.booking.cot.room.room_number,
        "building_name": student_access.booking.cot.room.floor.section.building.building_name,
        "amount": "",
        "utr": "",
        "bill_month": "",
        "grace_period_end_date": "",
        "admin_remark": student_access.reason,
    }
    return log_and_send("access_active", student_access.student, student_access.student.whatsapp_number, "access_active", context)
