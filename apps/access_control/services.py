from __future__ import annotations

from django.utils import timezone

from apps.bookings.models import BillPaymentStatusChoices, MonthlyRentDue

from .models import AccessStatusChoices, StudentAccess, StudentAccessHistory


def ensure_student_access_for_booking(booking):
    student_access, created = StudentAccess.objects.get_or_create(
        booking=booking,
        defaults={
            "student": booking.student,
            "access_status": AccessStatusChoices.ACTIVE,
            "reason": "Activated on booking confirmation",
            "valid_from": booking.booking_from_date,
            "valid_to": booking.booking_to_date,
        },
    )
    if not created:
        student_access.student = booking.student
        student_access.valid_from = booking.booking_from_date
        student_access.valid_to = booking.booking_to_date
        change_student_access_status(student_access, AccessStatusChoices.ACTIVE, "Activated on booking confirmation")
    return student_access


def change_student_access_status(student_access: StudentAccess, new_status: str, reason: str, changed_by=None):
    previous_status = student_access.access_status
    if previous_status == new_status and student_access.reason == reason:
        return student_access
    student_access.access_status = new_status
    student_access.reason = reason
    student_access.save(update_fields=["access_status", "reason", "updated_at"])
    StudentAccessHistory.objects.create(
        student_access=student_access,
        previous_status=previous_status,
        new_status=new_status,
        reason=reason,
        changed_by=changed_by,
    )
    return student_access


def sync_access_for_booking(booking, reference_date=None, changed_by=None):
    from apps.whatsapp.services import send_access_active_message, send_access_blocked_message

    reference_date = reference_date or timezone.localdate()
    student_access = ensure_student_access_for_booking(booking)
    current_bill = MonthlyRentDue.objects.filter(booking=booking, bill_month=reference_date.month, bill_year=reference_date.year).first()

    if current_bill and current_bill.payment_status == BillPaymentStatusChoices.PAID:
        was_blocked = student_access.access_status == AccessStatusChoices.BLOCKED
        change_student_access_status(student_access, AccessStatusChoices.ACTIVE, "Activated after payment confirmation", changed_by)
        if was_blocked:
            send_access_active_message(student_access, current_bill)
        return student_access

    if current_bill and current_bill.payment_status in [BillPaymentStatusChoices.UNPAID, BillPaymentStatusChoices.PENDING_VERIFICATION]:
        if current_bill.grace_period_end_date < reference_date:
            reason = f"Blocked due to unpaid rent for {reference_date.strftime('%B %Y')}"
            already_blocked = student_access.access_status == AccessStatusChoices.BLOCKED
            change_student_access_status(student_access, AccessStatusChoices.BLOCKED, reason, changed_by)
            if not already_blocked:
                current_bill.payment_status = BillPaymentStatusChoices.OVERDUE
                current_bill.save(update_fields=["payment_status", "updated_at"])
                send_access_blocked_message(current_bill)
            return student_access

    change_student_access_status(student_access, AccessStatusChoices.ACTIVE, "Access active", changed_by)
    return student_access


def bulk_update_access_status(reference_date=None, changed_by=None):
    reference_date = reference_date or timezone.localdate()
    updated = []
    for student_access in StudentAccess.objects.select_related("booking", "student"):
        updated.append(sync_access_for_booking(student_access.booking, reference_date=reference_date, changed_by=changed_by))
    return updated
