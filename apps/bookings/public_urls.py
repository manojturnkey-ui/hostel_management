from django.urls import path

from .views import BookingThankYouView, PublicBillPaymentView, PublicBookingCreateView


urlpatterns = [
    path("cots/<int:cot_id>/book/", PublicBookingCreateView.as_view(), name="public_booking_create"),
    path("thank-you/", BookingThankYouView.as_view(), name="public_booking_thank_you"),
    path("rent/pay/<uuid:reference>/", PublicBillPaymentView.as_view(), name="public_bill_payment"),
]
