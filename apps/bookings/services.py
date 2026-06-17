from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from random import SystemRandom

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.hostel.models import BillingCalculationChoices, Cot, CotStatusChoices, SystemSetting
from apps.payments.models import Payment, PaymentStatusChoices

from .models import (
    BillPaymentStatusChoices,
    BillTypeChoices,
    Booking,
    BookingStatusChoices,
    MonthlyRentDue,
    Student,
)


def get_system_setting():
    return SystemSetting.get_solo()


def generate_simple_credential(length: int = 8) -> str:
    characters = "abcdefghjkmnpqrstuvwxyz23456789"
    chooser = SystemRandom()
    return "".join(chooser.choice(characters) for _ in range(length))


def ensure_guest_user_for_student(student: Student):
    User = get_user_model()
    raw_password = generate_simple_credential(8)
    desired_username = student.mobile_number
    if student.guest_user_id:
        guest_user = student.guest_user
        guest_user.username = desired_username
        guest_user.display_name = student.full_name
        guest_user.mobile_number = student.mobile_number
    else:
        guest_user = User(
            username=desired_username,
            display_name=student.full_name,
            mobile_number=student.mobile_number,
            is_staff=False,
            is_superuser=False,
        )
    guest_user.set_password(raw_password)
    guest_user.is_active = True
    guest_user.email = ""
    guest_user.save()
    if student.guest_user_id != guest_user.pk:
        student.guest_user = guest_user
        student.save(update_fields=["guest_user"])
    return guest_user, raw_password


def calculate_first_bill_components(booking_from_date: date, monthly_rent: Decimal):
    setting = get_system_setting()
    total_days_in_month = calendar.monthrange(booking_from_date.year, booking_from_date.month)[1]
    month_end = date(booking_from_date.year, booking_from_date.month, total_days_in_month)

    if booking_from_date.day == 1:
        return {
            "bill_type": BillTypeChoices.REGULAR_MONTHLY,
            "billing_period_start": booking_from_date,
            "billing_period_end": month_end,
            "billable_days": total_days_in_month,
            "total_days_in_month": total_days_in_month,
            "bill_amount": monthly_rent.quantize(Decimal("0.01")),
        }

    effective_start = booking_from_date
    if setting.billing_calculation_method == BillingCalculationChoices.EXCLUSIVE_START:
        effective_start = booking_from_date + timedelta(days=1)
    billable_days = max((month_end - effective_start).days + 1, 0)
    daily_rent = (monthly_rent / Decimal(total_days_in_month)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    bill_amount = (daily_rent * billable_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "bill_type": BillTypeChoices.PARTIAL_FIRST_MONTH,
        "billing_period_start": booking_from_date,
        "billing_period_end": month_end,
        "billable_days": billable_days,
        "total_days_in_month": total_days_in_month,
        "bill_amount": bill_amount,
    }


def estimate_booking_total(cot, booking_from_date: date):
    first_bill = calculate_first_bill_components(booking_from_date, Decimal(cot.cot_price))
    security_deposit = Decimal(cot.security_deposit or Decimal("0.00"))
    total_amount = (first_bill["bill_amount"] + security_deposit).quantize(Decimal("0.01"))
    return {
        "monthly_rent": Decimal(cot.cot_price).quantize(Decimal("0.01")),
        "security_deposit": security_deposit.quantize(Decimal("0.01")),
        "first_rent_amount": first_bill["bill_amount"],
        "total_amount": total_amount,
    }


def get_or_create_student_from_public_form(cleaned_data: dict) -> Student:
    student = Student.objects.filter(mobile_number=cleaned_data["mobile_number"]).order_by("-created_at").first()
    fields = {
        "full_name": cleaned_data["full_name"],
        "mobile_number": cleaned_data["mobile_number"],
        "whatsapp_number": cleaned_data["whatsapp_number"],
        "relative_contact_number": cleaned_data.get("relative_contact_number", ""),
        "education": "",
        "purpose_for_cot_booking": "",
        "address": cleaned_data["address"],
        "city_village": "",
        "state": cleaned_data["state"],
        "pincode": cleaned_data["pincode"],
        "student_photo": cleaned_data.get("student_photo"),
        "address_proof_type": cleaned_data["address_proof_type"],
        "address_proof_front": cleaned_data["address_proof_front"],
        "address_proof_back": cleaned_data.get("address_proof_back"),
    }
    if student:
        for key, value in fields.items():
            if value not in [None, ""] or key in ["purpose_for_cot_booking", "address_proof_type", "address_proof_front"]:
                setattr(student, key, value)
        student.full_clean()
        student.save()
        return student
    student = Student(**fields)
    student.full_clean()
    student.save()
    return student


@transaction.atomic
def create_public_booking(cot, cleaned_data: dict) -> dict:
    from apps.whatsapp.services import (
        send_booking_submitted_message,
        send_guest_portal_credentials_message,
        send_payment_pending_message,
    )

    cot = cot.__class__.objects.select_for_update().select_related("room__floor__section__building__area").get(pk=cot.pk)
    if cot.status != CotStatusChoices.AVAILABLE:
        raise ValueError("This cot is not available for booking.")

    student = get_or_create_student_from_public_form(cleaned_data)
    guest_user, raw_password = ensure_guest_user_for_student(student)
    estimates = estimate_booking_total(cot, cleaned_data["booking_from_date"])
    booking = Booking(
        student=student,
        cot=cot,
        booking_from_date=cleaned_data["booking_from_date"],
        monthly_rent=estimates["monthly_rent"],
        security_deposit=estimates["security_deposit"],
        total_amount=estimates["total_amount"],
        booking_status=BookingStatusChoices.PENDING_ADMIN_CONFIRMATION,
    )
    booking.full_clean()
    booking.save()
    payment = Payment(
        booking=booking,
        amount=estimates["total_amount"],
        utr_transaction_id=cleaned_data["utr_transaction_id"],
        payment_screenshot=cleaned_data["payment_screenshot"],
        payment_status=PaymentStatusChoices.PENDING,
    )
    payment.full_clean()
    payment.save()
    cot.status = CotStatusChoices.PENDING
    cot.save(update_fields=["status", "updated_at"])
    send_booking_submitted_message(booking)
    send_guest_portal_credentials_message(booking, guest_user.username, raw_password)
    send_payment_pending_message(booking)
    return {
        "booking": booking,
        "guest_user": guest_user,
        "guest_password": raw_password,
    }


def build_bill_dates(bill_year: int, bill_month: int, booking_from_date: date):
    setting = get_system_setting()
    if bill_year == booking_from_date.year and bill_month == booking_from_date.month and booking_from_date.day != 1:
        due_date = booking_from_date
        grace_period_end_date = booking_from_date + timedelta(days=setting.grace_period_days)
    else:
        due_date = date(bill_year, bill_month, setting.payment_window_start_day)
        grace_period_end_date = date(bill_year, bill_month, setting.payment_window_end_day)
    return due_date, grace_period_end_date


def generate_bill_for_month(booking: Booking, bill_year: int, bill_month: int, auto_mark_paid: bool = False, source_payment=None, manual_data: dict | None = None):
    from apps.whatsapp.services import send_first_bill_generated_message, send_monthly_bill_generated_message

    existing_bill = MonthlyRentDue.objects.filter(booking=booking, bill_year=bill_year, bill_month=bill_month).first()
    if existing_bill:
        return existing_bill, False

    bill = MonthlyRentDue(booking=booking, bill_year=bill_year, bill_month=bill_month)

    if manual_data:
        bill.student = booking.student
        bill.billing_period_start = manual_data["billing_period_start"]
        bill.billing_period_end = manual_data["billing_period_end"]
        bill.monthly_rent = booking.monthly_rent
        bill.bill_amount = manual_data["bill_amount"]
        bill.bill_type = BillTypeChoices.MANUAL
        bill.total_days_in_month = calendar.monthrange(bill_year, bill_month)[1]
        bill.billable_days = (manual_data["billing_period_end"] - manual_data["billing_period_start"]).days + 1
        bill.due_date = manual_data["due_date"]
        bill.grace_period_end_date = manual_data["grace_period_end_date"]
        bill.payment_status = BillPaymentStatusChoices.UNPAID
        bill.admin_remark = manual_data.get("admin_remark", "")
        bill.save()
        send_monthly_bill_generated_message(bill)
        return bill, True

    if booking.booking_from_date.year == bill_year and booking.booking_from_date.month == bill_month:
        first_bill = calculate_first_bill_components(booking.booking_from_date, booking.monthly_rent)
        billing_period_start = first_bill["billing_period_start"]
        billing_period_end = first_bill["billing_period_end"]
        bill_type = first_bill["bill_type"]
        total_days_in_month = first_bill["total_days_in_month"]
        billable_days = first_bill["billable_days"]
        bill_amount = first_bill["bill_amount"]
    else:
        total_days_in_month = calendar.monthrange(bill_year, bill_month)[1]
        billing_period_start = date(bill_year, bill_month, 1)
        billing_period_end = date(bill_year, bill_month, total_days_in_month)
        bill_type = BillTypeChoices.REGULAR_MONTHLY
        billable_days = total_days_in_month
        bill_amount = booking.monthly_rent

    due_date, grace_period_end_date = build_bill_dates(bill_year, bill_month, booking.booking_from_date)
    bill.student = booking.student
    bill.billing_period_start = billing_period_start
    bill.billing_period_end = billing_period_end
    bill.monthly_rent = booking.monthly_rent
    bill.bill_amount = Decimal(bill_amount).quantize(Decimal("0.01"))
    bill.bill_type = bill_type
    bill.total_days_in_month = total_days_in_month
    bill.billable_days = billable_days
    bill.due_date = due_date
    bill.grace_period_end_date = grace_period_end_date
    bill.payment_status = BillPaymentStatusChoices.PAID if auto_mark_paid else BillPaymentStatusChoices.UNPAID

    if auto_mark_paid and source_payment:
        bill.payment_date = source_payment.created_at
        bill.utr_transaction_id = source_payment.utr_transaction_id
        bill.payment_screenshot = source_payment.payment_screenshot
        bill.confirmed_by = source_payment.confirmed_by
        bill.confirmed_at = source_payment.confirmed_at

    bill.save()
    if not auto_mark_paid:
        if booking.booking_from_date.year == bill_year and booking.booking_from_date.month == bill_month:
            send_first_bill_generated_message(bill)
        else:
            send_monthly_bill_generated_message(bill)
    return bill, True


@transaction.atomic
def confirm_booking_payment(payment: Payment, user, remark: str = "") -> Payment:
    from apps.access_control.services import ensure_student_access_for_booking
    from apps.whatsapp.services import send_booking_confirmed_message, send_payment_received_message

    booking = payment.booking
    if booking.booking_status == BookingStatusChoices.CONFIRMED:
        return payment

    payment.payment_status = PaymentStatusChoices.CONFIRMED
    payment.admin_remark = remark
    payment.confirmed_by = user
    payment.confirmed_at = timezone.now()
    payment.save()

    booking.booking_status = BookingStatusChoices.CONFIRMED
    booking.admin_remark = remark
    booking.confirmed_by = user
    booking.confirmed_at = timezone.now()
    booking.save()

    booking.cot.status = CotStatusChoices.OCCUPIED
    booking.cot.save(update_fields=["status", "updated_at"])

    generate_bill_for_month(
        booking,
        bill_year=booking.booking_from_date.year,
        bill_month=booking.booking_from_date.month,
        auto_mark_paid=True,
        source_payment=payment,
    )
    ensure_student_access_for_booking(booking)
    send_booking_confirmed_message(booking)
    send_payment_received_message(payment)
    return payment


@transaction.atomic
def reject_booking_payment(payment: Payment, user, remark: str) -> Payment:
    from apps.whatsapp.services import send_booking_rejected_message

    booking = payment.booking
    payment.payment_status = PaymentStatusChoices.REJECTED
    payment.admin_remark = remark
    payment.confirmed_by = user
    payment.confirmed_at = timezone.now()
    payment.save()

    booking.booking_status = BookingStatusChoices.REJECTED
    booking.admin_remark = remark
    booking.confirmed_by = user
    booking.confirmed_at = timezone.now()
    booking.save()

    booking.cot.status = CotStatusChoices.AVAILABLE
    booking.cot.save(update_fields=["status", "updated_at"])
    send_booking_rejected_message(booking)
    return payment


@transaction.atomic
def cancel_booking(booking: Booking, user, remark: str = "") -> Booking:
    from apps.access_control.models import AccessStatusChoices
    from apps.access_control.services import change_student_access_status

    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    cot = Cot.objects.select_for_update().get(pk=booking.cot_id)
    payment = Payment.objects.select_for_update().filter(booking=booking).first()
    monthly_dues = MonthlyRentDue.objects.select_for_update().filter(booking=booking)
    if booking.booking_status == BookingStatusChoices.CANCELLED:
        return booking

    action_time = timezone.now()
    final_remark = remark or "Booking cancelled by admin."

    booking.booking_status = BookingStatusChoices.CANCELLED
    booking.admin_remark = final_remark
    booking.confirmed_by = user
    booking.confirmed_at = action_time
    if not booking.booking_to_date:
        booking.booking_to_date = timezone.localdate()
    booking.save(update_fields=["booking_status", "admin_remark", "confirmed_by", "confirmed_at", "booking_to_date", "updated_at"])

    if payment:
        payment.admin_remark = final_remark
        if payment.payment_status == PaymentStatusChoices.PENDING:
            payment.payment_status = PaymentStatusChoices.REJECTED
            payment.confirmed_by = user
            payment.confirmed_at = action_time
            payment.save(update_fields=["payment_status", "admin_remark", "confirmed_by", "confirmed_at", "updated_at"])
        else:
            payment.save(update_fields=["admin_remark", "updated_at"])

    monthly_dues.exclude(payment_status=BillPaymentStatusChoices.PAID).update(
        payment_status=BillPaymentStatusChoices.CANCELLED,
        admin_remark=final_remark,
        confirmed_by=user,
        confirmed_at=action_time,
        updated_at=action_time,
    )

    cot.status = CotStatusChoices.AVAILABLE
    cot.save(update_fields=["status", "updated_at"])

    try:
        student_access = booking.student_access
    except ObjectDoesNotExist:
        student_access = None

    if student_access:
        change_student_access_status(
            student_access,
            AccessStatusChoices.INACTIVE,
            "Booking cancelled by admin",
            changed_by=user,
        )

    return booking


def submit_monthly_bill_payment(bill: MonthlyRentDue, cleaned_data: dict):
    bill.utr_transaction_id = cleaned_data["utr_transaction_id"]
    bill.payment_screenshot = cleaned_data["payment_screenshot"]
    bill.payment_status = BillPaymentStatusChoices.PENDING_VERIFICATION
    bill.payment_date = timezone.now()
    bill.save(update_fields=["utr_transaction_id", "payment_screenshot", "payment_status", "payment_date", "updated_at"])
    return bill


def confirm_monthly_bill_payment(bill: MonthlyRentDue, user, remark: str = ""):
    from apps.access_control.services import sync_access_for_booking
    from apps.whatsapp.services import send_payment_received_message

    bill.payment_status = BillPaymentStatusChoices.PAID
    bill.admin_remark = remark
    bill.confirmed_by = user
    bill.confirmed_at = timezone.now()
    if not bill.payment_date:
        bill.payment_date = timezone.now()
    bill.save()
    sync_access_for_booking(bill.booking, reference_date=timezone.localdate(), changed_by=user)
    send_payment_received_message(bill)
    return bill


def reject_monthly_bill_payment(bill: MonthlyRentDue, user, remark: str):
    from apps.access_control.services import sync_access_for_booking

    bill.payment_status = BillPaymentStatusChoices.UNPAID
    bill.admin_remark = remark
    bill.confirmed_by = user
    bill.confirmed_at = timezone.now()
    bill.save()
    sync_access_for_booking(bill.booking, reference_date=timezone.localdate(), changed_by=user)
    return bill


def extend_bill_grace_period(bill: MonthlyRentDue, new_date: date, remark: str, user=None):
    from apps.access_control.services import sync_access_for_booking

    bill.grace_period_end_date = new_date
    bill.admin_remark = remark
    if user:
        bill.confirmed_by = user
    bill.save()
    sync_access_for_booking(bill.booking, reference_date=timezone.localdate(), changed_by=user)
    return bill


def generate_current_month_bills(reference_date: date | None = None):
    reference_date = reference_date or timezone.localdate()
    generated = []
    bookings = Booking.objects.filter(booking_status=BookingStatusChoices.CONFIRMED).select_related("student", "cot")
    for booking in bookings:
        if booking.booking_to_date and booking.booking_to_date < reference_date:
            continue
        bill, created = generate_bill_for_month(booking, reference_date.year, reference_date.month)
        if created:
            generated.append(bill)
    return generated


def send_due_and_grace_reminders(reference_date: date | None = None) -> int:
    from apps.whatsapp.models import WhatsAppLog
    from apps.whatsapp.services import send_grace_period_ending_reminder_message, send_payment_reminder_message

    reference_date = reference_date or timezone.localdate()
    reminders_sent = 0
    bills = (
        MonthlyRentDue.objects.filter(
            payment_status__in=[BillPaymentStatusChoices.UNPAID, BillPaymentStatusChoices.PENDING_VERIFICATION],
            booking__booking_status=BookingStatusChoices.CONFIRMED,
        )
        .select_related("student", "booking__cot__room__floor__section__building__area")
        .order_by("billing_period_start")
    )
    for bill in bills:
        payment_reminder_date = max(bill.due_date - timedelta(days=1), bill.billing_period_start)
        grace_reminder_date = max(bill.grace_period_end_date - timedelta(days=1), bill.billing_period_start)

        if reference_date == payment_reminder_date and not WhatsAppLog.objects.filter(
            student=bill.student,
            event_type="payment_reminder",
            created_at__date=reference_date,
        ).exists():
            send_payment_reminder_message(bill)
            reminders_sent += 1

        if reference_date == grace_reminder_date and not WhatsAppLog.objects.filter(
            student=bill.student,
            event_type="grace_period_ending_reminder",
            created_at__date=reference_date,
        ).exists():
            send_grace_period_ending_reminder_message(bill)
            reminders_sent += 1
    return reminders_sent
