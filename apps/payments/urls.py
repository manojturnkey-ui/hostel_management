from django.urls import path

from .views import (
    ConfirmPaymentView,
    PaymentDetailView,
    PaymentHistoryView,
    PendingPaymentListView,
    QRCodeSettingCreateView,
    QRCodeSettingListView,
    QRCodeSettingUpdateView,
    RejectPaymentView,
)


urlpatterns = [
    path("payments/", PendingPaymentListView.as_view(), name="panel_pending_payment_list"),
    path("payments/history/", PaymentHistoryView.as_view(), name="panel_payment_history"),
    path("payments/<int:pk>/", PaymentDetailView.as_view(), name="panel_payment_detail"),
    path("payments/<int:pk>/confirm/", ConfirmPaymentView.as_view(), name="panel_payment_confirm"),
    path("payments/<int:pk>/reject/", RejectPaymentView.as_view(), name="panel_payment_reject"),
    path("qr-settings/", QRCodeSettingListView.as_view(), name="panel_qr_setting_list"),
    path("qr-settings/add/", QRCodeSettingCreateView.as_view(), name="panel_qr_setting_create"),
    path("qr-settings/<int:pk>/edit/", QRCodeSettingUpdateView.as_view(), name="panel_qr_setting_update"),
]
