from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.settings import BASE_DIR, env

from .models import WhatsAppLog, WhatsAppLogStatusChoices, WhatsAppMessageTemplate, WhatsAppSetting


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


@dataclass
class GatewayResponse:
    ok: bool
    status_code: int | None
    data: dict
    error: str = ""

    @property
    def summary(self) -> str:
        if self.error:
            return self.error
        if isinstance(self.data, dict):
            return str(self.data.get("message") or self.data.get("state") or "OK")
        return "OK"


@dataclass
class DashboardStatus:
    configured: bool
    reachable: bool
    connected: bool
    state: str
    number: str
    last_error: str
    qr_image_data_url: str
    raw: dict


def ensure_default_templates() -> None:
    for template_key, content in DEFAULT_TEMPLATES.items():
        WhatsAppMessageTemplate.objects.get_or_create(
            template_key=template_key,
            defaults={"title": template_key.replace("_", " ").title(), "content": content, "is_active": True},
        )


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def get_local_scan_folder_env() -> dict[str, str]:
    primary_path = BASE_DIR / "whatsapp_scan" / "whatsapp scan" / ".env"
    fallback_path = BASE_DIR / "whatsapp_scan" / "whatsapp scan" / ".env.example"
    return read_env_file(primary_path) or read_env_file(fallback_path)


def get_active_setting() -> WhatsAppSetting | None:
    local_scan_env = get_local_scan_folder_env()
    port = local_scan_env.get("PORT", "3001")
    service_url = (env("WHATSAPP_SCAN_BASE_URL", "") or f"http://127.0.0.1:{port}").strip().rstrip("/")
    api_key = (env("WHATSAPP_SCAN_API_KEY", "") or local_scan_env.get("WHATSAPP_SCAN_API_KEY", "")).strip()
    if not service_url or not api_key:
        return None

    fallback = WhatsAppSetting(
        service_name="Integrated WhatsApp Scan",
        service_url=service_url,
        api_key=api_key,
        default_country_code=env("WHATSAPP_SCAN_DEFAULT_COUNTRY_CODE", local_scan_env.get("DEFAULT_COUNTRY_CODE", "91")) or "91",
        session_name=env("WHATSAPP_SCAN_SESSION_NAME", local_scan_env.get("SESSION_NAME", "")) or "",
        is_active=True,
    )
    fallback.pk = None
    return fallback


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


def build_gateway_url(service_url: str, endpoint: str) -> str:
    return f"{service_url.rstrip('/')}/{endpoint.lstrip('/')}"


def decode_json_response(raw: bytes) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"raw": raw.decode("utf-8", errors="ignore")}


def gateway_request(setting: WhatsAppSetting | None, endpoint: str, method: str = "GET", payload: dict | None = None) -> GatewayResponse:
    if not setting:
        return GatewayResponse(False, None, {}, "WhatsApp scan service is not configured.")

    service_url = (setting.service_url or "").strip().rstrip("/")
    api_key = (setting.api_key or "").strip()
    if not service_url or not api_key:
        return GatewayResponse(False, None, {}, "WhatsApp scan service URL or API key is missing.")

    request_data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(build_gateway_url(service_url, endpoint), data=request_data, method=method.upper())
    request.add_header("Accept", "application/json")
    request.add_header("x-api-key", api_key)
    if request_data is not None:
        request.add_header("Content-Type", "application/json")

    timeout = max(3, int(env("WHATSAPP_SCAN_TIMEOUT", "15") or "15"))

    try:
        with urlopen(request, timeout=timeout) as response:
            payload_data = decode_json_response(response.read())
            return GatewayResponse(True, getattr(response, "status", 200), payload_data, "")
    except HTTPError as exc:
        payload_data = decode_json_response(exc.read())
        message = payload_data.get("message") if isinstance(payload_data, dict) else ""
        return GatewayResponse(False, exc.code, payload_data, message or str(exc))
    except URLError as exc:
        return GatewayResponse(False, None, {}, f"WhatsApp scan service is unreachable: {exc.reason}")
    except Exception as exc:
        return GatewayResponse(False, None, {}, f"Unexpected WhatsApp scan error: {exc}")


def fetch_gateway_status(setting: WhatsAppSetting | None = None) -> DashboardStatus:
    setting = setting or get_active_setting()
    configured = bool(setting and setting.service_url and setting.api_key)
    if not configured:
        return DashboardStatus(False, False, False, "not_configured", "", "Configure the WhatsApp scan service first.", "", {})

    response = gateway_request(setting, "/status")
    if not response.ok:
        return DashboardStatus(True, False, False, "offline", "", response.summary, "", response.data)

    data = response.data
    return DashboardStatus(
        configured=True,
        reachable=True,
        connected=bool(data.get("connected")),
        state=str(data.get("state") or "unknown"),
        number=str(data.get("number") or ""),
        last_error=str(data.get("lastError") or ""),
        qr_image_data_url="",
        raw=data,
    )


def fetch_gateway_qr(setting: WhatsAppSetting | None = None) -> GatewayResponse:
    setting = setting or get_active_setting()
    return gateway_request(setting, "/qr")


def restart_gateway_session(setting: WhatsAppSetting | None = None) -> GatewayResponse:
    setting = setting or get_active_setting()
    return gateway_request(setting, "/restart", method="POST", payload={})


def logout_gateway_session(setting: WhatsAppSetting | None = None) -> GatewayResponse:
    setting = setting or get_active_setting()
    return gateway_request(setting, "/logout", method="POST", payload={})


def send_gateway_message(mobile_number: str, message: str, setting: WhatsAppSetting | None = None) -> GatewayResponse:
    setting = setting or get_active_setting()
    return gateway_request(setting, "/send", method="POST", payload={"phone": mobile_number, "message": message})


def log_and_send(template_key: str, student, mobile_number: str, event_type: str, context: dict) -> WhatsAppLog:
    message = render_template(template_key, context)
    gateway_response = send_gateway_message(mobile_number, message)
    status = WhatsAppLogStatusChoices.SENT if gateway_response.ok and gateway_response.data.get("success", True) else WhatsAppLogStatusChoices.FAILED
    return WhatsAppLog.objects.create(
        student=student,
        mobile_number=mobile_number,
        event_type=event_type,
        message=message,
        status=status,
        response=gateway_response.summary,
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


def send_guest_portal_credentials_message(booking, username: str, password: str):
    message = (
        f"Dear {booking.student.full_name}, your guest login is ready.\n"
        f"Username: {username}\n"
        f"Password: {password}\n"
        "Use these credentials to track your booking status and latest payment."
    )
    gateway_response = send_gateway_message(booking.student.whatsapp_number, message)
    status = WhatsAppLogStatusChoices.SENT if gateway_response.ok and gateway_response.data.get("success", True) else WhatsAppLogStatusChoices.FAILED
    return WhatsAppLog.objects.create(
        student=booking.student,
        mobile_number=booking.student.whatsapp_number,
        event_type="guest_credentials",
        message=message,
        status=status,
        response=gateway_response.summary,
    )


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
