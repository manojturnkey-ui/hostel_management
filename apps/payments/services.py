from .models import Payment, QRCodeSetting


def get_active_qr_setting():
    return QRCodeSetting.objects.filter(is_active=True).order_by("-created_at").first()


def confirm_booking_payment(payment: Payment, user, remark: str = "") -> Payment:
    from apps.bookings.services import confirm_booking_payment

    return confirm_booking_payment(payment, user, remark)


def reject_booking_payment(payment: Payment, user, remark: str) -> Payment:
    from apps.bookings.services import reject_booking_payment

    return reject_booking_payment(payment, user, remark)
