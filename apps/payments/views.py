from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView

from .forms import PaymentReviewForm, QRCodeSettingForm
from .models import Payment, PaymentStatusChoices, QRCodeSetting
from .services import confirm_booking_payment, reject_booking_payment


class PendingPaymentListView(PanelListView):
    model = Payment
    page_title = "Pending Payment Verification"
    page_subtitle = "Booking payments waiting for admin confirmation"
    detail_url_name = "panel_payment_detail"
    columns = [
        {"label": "Student", "value": "booking.student.full_name"},
        {"label": "Cot", "value": "booking.cot.cot_number"},
        {"label": "Room", "value": "booking.cot.room.room_number"},
        {"label": "Amount", "value": "amount"},
        {"label": "UTR", "value": "utr_transaction_id"},
        {"label": "Status", "value": "payment_status"},
    ]
    search_fields = ["booking__student__full_name", "utr_transaction_id", "booking__cot__room__room_number"]

    def get_queryset(self):
        return super().get_queryset().filter(payment_status=PaymentStatusChoices.PENDING).select_related("booking__student", "booking__cot__room")


class PaymentHistoryView(PanelListView):
    model = Payment
    page_title = "Payment History"
    page_subtitle = "All booking payment records"
    detail_url_name = "panel_payment_detail"
    columns = [
        {"label": "Student", "value": "booking.student.full_name"},
        {"label": "Amount", "value": "amount"},
        {"label": "UTR", "value": "utr_transaction_id"},
        {"label": "Method", "value": "payment_method"},
        {"label": "Status", "value": "payment_status"},
        {"label": "Created", "value": "created_at"},
    ]
    search_fields = ["booking__student__full_name", "utr_transaction_id"]


class PaymentDetailView(PanelLoginRequiredMixin, DetailView):
    model = Payment
    template_name = "admin_panel/payments/detail.html"
    context_object_name = "payment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Payment Detail",
                "page_subtitle": "Verify UTR, screenshot, and student details",
                "review_form": PaymentReviewForm(),
            }
        )
        return context


class ConfirmPaymentView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        confirm_booking_payment(payment, request.user, request.POST.get("admin_remark", ""))
        messages.success(request, "Payment confirmed successfully.")
        return redirect("panel_payment_detail", pk=pk)


class RejectPaymentView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        remark = request.POST.get("admin_remark", "").strip()
        if not remark:
            messages.error(request, "Admin remark is required when rejecting a payment.")
            return redirect("panel_payment_detail", pk=pk)
        reject_booking_payment(payment, request.user, remark)
        messages.warning(request, "Payment rejected successfully.")
        return redirect("panel_payment_detail", pk=pk)


class QRCodeSettingListView(PanelListView):
    model = QRCodeSetting
    page_title = "QR Settings"
    page_subtitle = "Manage active UPI QR codes for student payments"
    create_url_name = "panel_qr_setting_create"
    update_url_name = "panel_qr_setting_update"
    columns = [
        {"label": "Title", "value": "title"},
        {"label": "UPI ID", "value": "upi_id"},
        {"label": "Account Name", "value": "account_name"},
        {"label": "Active", "value": "is_active"},
        {"label": "Created", "value": "created_at"},
    ]
    search_fields = ["title", "upi_id", "account_name"]


class QRCodeSettingCreateView(PanelCreateView):
    model = QRCodeSetting
    form_class = QRCodeSettingForm
    page_title = "Create QR Setting"
    back_url_name = "panel_qr_setting_list"
    success_message = "QR payment setting created successfully."
    success_url = reverse_lazy("panel_qr_setting_list")


class QRCodeSettingUpdateView(PanelUpdateView):
    model = QRCodeSetting
    form_class = QRCodeSettingForm
    page_title = "Update QR Setting"
    back_url_name = "panel_qr_setting_list"
    success_message = "QR payment setting updated successfully."
    success_url = reverse_lazy("panel_qr_setting_list")
