from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelListView
from apps.hostel.models import Cot, CotStatusChoices
from apps.payments.services import get_active_qr_setting

from .forms import BookingReviewForm, GraceExtensionForm, ManualBillGenerateForm, MonthlyRentPaymentForm, PublicBookingForm
from .models import BillPaymentStatusChoices, Booking, BookingStatusChoices, MonthlyRentDue, Student
from .services import (
    confirm_booking_payment,
    confirm_monthly_bill_payment,
    create_public_booking,
    estimate_booking_total,
    extend_bill_grace_period,
    generate_bill_for_month,
    reject_booking_payment,
    reject_monthly_bill_payment,
    submit_monthly_bill_payment,
)


class StudentListView(PanelListView):
    model = Student
    page_title = "Students"
    page_subtitle = "Student profile and document records"
    columns = [
        {"label": "Student Name", "value": "full_name"},
        {"label": "Mobile", "value": "mobile_number"},
        {"label": "WhatsApp", "value": "whatsapp_number"},
        {"label": "City / Village", "value": "city_village"},
        {"label": "Created", "value": "created_at"},
    ]
    search_fields = ["full_name", "mobile_number", "whatsapp_number", "city_village"]


class BookingStatusListView(PanelListView):
    model = Booking
    detail_url_name = "panel_booking_detail"
    columns = [
        {"label": "Student", "value": "student.full_name"},
        {"label": "Cot", "value": "cot.cot_number"},
        {"label": "Room", "value": "cot.room.room_number"},
        {"label": "Monthly Rent", "value": "monthly_rent"},
        {"label": "Status", "value": "booking_status"},
        {"label": "Created", "value": "created_at"},
    ]
    search_fields = ["student__full_name", "student__mobile_number", "cot__cot_number", "cot__room__room_number"]
    status_filter = None

    def get_queryset(self):
        queryset = super().get_queryset().select_related("student", "cot", "cot__room")
        if self.status_filter:
            queryset = queryset.filter(booking_status=self.status_filter)
        return queryset


class PendingBookingListView(BookingStatusListView):
    page_title = "Pending Bookings"
    page_subtitle = "Bookings waiting for payment verification"
    status_filter = BookingStatusChoices.PENDING_ADMIN_CONFIRMATION


class ConfirmedBookingListView(BookingStatusListView):
    page_title = "Confirmed Bookings"
    page_subtitle = "Currently confirmed cot allotments"
    status_filter = BookingStatusChoices.CONFIRMED


class RejectedBookingListView(BookingStatusListView):
    page_title = "Rejected Bookings"
    page_subtitle = "Rejected or failed booking requests"
    status_filter = BookingStatusChoices.REJECTED


class BookingDetailView(PanelLoginRequiredMixin, DetailView):
    model = Booking
    template_name = "admin_panel/bookings/detail.html"
    context_object_name = "booking"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Booking Detail",
                "page_subtitle": "Review student profile, payment, and cot status",
                "review_form": BookingReviewForm(),
            }
        )
        return context


class ConfirmBookingView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_related("payment"), pk=pk)
        remark = request.POST.get("admin_remark", "")
        confirm_booking_payment(booking.payment, request.user, remark)
        messages.success(request, "Booking and payment confirmed successfully.")
        return redirect("panel_booking_detail", pk=pk)


class RejectBookingView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_related("payment"), pk=pk)
        remark = request.POST.get("admin_remark", "").strip()
        if not remark:
            messages.error(request, "Admin remark is required when rejecting a booking.")
            return redirect("panel_booking_detail", pk=pk)
        reject_booking_payment(booking.payment, request.user, remark)
        messages.warning(request, "Booking rejected successfully.")
        return redirect("panel_booking_detail", pk=pk)


class BillListView(PanelListView):
    model = MonthlyRentDue
    detail_url_name = "panel_bill_detail"
    columns = [
        {"label": "Student", "value": "student.full_name"},
        {"label": "Bill Month", "value": "bill_month"},
        {"label": "Bill Year", "value": "bill_year"},
        {"label": "Bill Amount", "value": "bill_amount"},
        {"label": "Status", "value": "payment_status"},
        {"label": "Grace Ends", "value": "grace_period_end_date"},
    ]
    search_fields = ["student__full_name", "utr_transaction_id", "booking__cot__room__room_number"]


class CurrentMonthBillListView(BillListView):
    page_title = "Current Month Bills"
    page_subtitle = "Current cycle billing overview"

    def get_queryset(self):
        today = timezone.localdate()
        return super().get_queryset().filter(bill_month=today.month, bill_year=today.year)


class PendingBillListView(BillListView):
    page_title = "Pending Bill Verification"
    page_subtitle = "Monthly rent payments awaiting approval"

    def get_queryset(self):
        return super().get_queryset().filter(payment_status=BillPaymentStatusChoices.PENDING_VERIFICATION)


class PaidBillListView(BillListView):
    page_title = "Paid Bills"
    page_subtitle = "Confirmed monthly rent payments"

    def get_queryset(self):
        return super().get_queryset().filter(payment_status=BillPaymentStatusChoices.PAID)


class UnpaidBillListView(BillListView):
    page_title = "Unpaid Bills"
    page_subtitle = "Bills not yet submitted for verification"

    def get_queryset(self):
        return super().get_queryset().filter(payment_status=BillPaymentStatusChoices.UNPAID)


class OverdueBillListView(BillListView):
    page_title = "Overdue Bills"
    page_subtitle = "Bills that passed the grace period"

    def get_queryset(self):
        return super().get_queryset().filter(payment_status=BillPaymentStatusChoices.OVERDUE)


class StudentLedgerView(BillListView):
    template_name = "admin_panel/billing/ledger.html"
    page_title = "Student Ledger"
    page_subtitle = "Ledger of rent bills and payment status"
    columns = [
        {"label": "Student", "value": "student.full_name"},
        {"label": "Mobile", "value": "student.mobile_number"},
        {"label": "Room", "value": "booking.cot.room.room_number"},
        {"label": "Cot", "value": "booking.cot.cot_number"},
        {"label": "Monthly Rent", "value": "monthly_rent"},
        {"label": "Bill Period", "value": "billing_period_start"},
        {"label": "Bill Amount", "value": "bill_amount"},
        {"label": "Status", "value": "payment_status"},
        {"label": "UTR", "value": "utr_transaction_id"},
        {"label": "Confirmed At", "value": "confirmed_at"},
        {"label": "Balance", "value": "balance_amount"},
    ]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("student", "booking__cot__room")
        search = self.request.GET.get("student", "").strip()
        if search:
            queryset = queryset.filter(
                Q(student__full_name__icontains=search)
                | Q(student__mobile_number__icontains=search)
                | Q(booking__cot__room__room_number__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_search"] = self.request.GET.get("student", "")
        return context


class BillDetailView(PanelLoginRequiredMixin, DetailView):
    model = MonthlyRentDue
    template_name = "admin_panel/billing/detail.html"
    context_object_name = "bill"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Bill Detail",
                "page_subtitle": "Review bill, screenshot, and ledger details",
                "review_form": BookingReviewForm(),
                "grace_form": GraceExtensionForm(initial={"grace_period_end_date": self.object.grace_period_end_date}),
                "public_payment_url": self.request.build_absolute_uri(
                    reverse_lazy("public_bill_payment", kwargs={"reference": self.object.public_reference})
                ),
            }
        )
        return context


class ConfirmBillPaymentView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        bill = get_object_or_404(MonthlyRentDue, pk=pk)
        confirm_monthly_bill_payment(bill, request.user, request.POST.get("admin_remark", ""))
        messages.success(request, "Monthly bill payment confirmed.")
        return redirect("panel_bill_detail", pk=pk)


class RejectBillPaymentView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        bill = get_object_or_404(MonthlyRentDue, pk=pk)
        remark = request.POST.get("admin_remark", "").strip()
        if not remark:
            messages.error(request, "Admin remark is required when rejecting a monthly payment.")
            return redirect("panel_bill_detail", pk=pk)
        reject_monthly_bill_payment(bill, request.user, remark)
        messages.warning(request, "Monthly bill payment marked unpaid.")
        return redirect("panel_bill_detail", pk=pk)


class ManualBillGenerateView(PanelLoginRequiredMixin, FormView):
    template_name = "admin_panel/billing/manual_generate.html"
    form_class = ManualBillGenerateForm
    success_url = reverse_lazy("panel_manual_bill_generate")

    def form_valid(self, form):
        booking = form.cleaned_data["booking"]
        generate_bill_for_month(
            booking,
            bill_year=form.cleaned_data["bill_year"],
            bill_month=form.cleaned_data["bill_month"],
            manual_data=form.cleaned_data,
        )
        messages.success(self.request, "Manual bill generated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Manual Bill Generate", "page_subtitle": "Generate a one-off or corrected bill"})
        return context


class ManualGraceExtensionView(BillListView):
    page_title = "Manual Grace Extension"
    page_subtitle = "Select a bill and extend its grace period if required"

    def get_queryset(self):
        return super().get_queryset().filter(
            payment_status__in=[BillPaymentStatusChoices.UNPAID, BillPaymentStatusChoices.PENDING_VERIFICATION, BillPaymentStatusChoices.OVERDUE]
        )


class ExtendBillGracePeriodView(PanelLoginRequiredMixin, View):
    def post(self, request, pk):
        bill = get_object_or_404(MonthlyRentDue, pk=pk)
        form = GraceExtensionForm(request.POST)
        if form.is_valid():
            extend_bill_grace_period(
                bill,
                form.cleaned_data["grace_period_end_date"],
                form.cleaned_data["admin_remark"],
                request.user,
            )
            messages.success(request, "Grace period extended successfully.")
        else:
            messages.error(request, "Please provide a valid grace-period end date.")
        return redirect("panel_bill_detail", pk=pk)


class PublicBookingCreateView(FormView):
    template_name = "public/booking_form.html"
    form_class = PublicBookingForm

    def dispatch(self, request, *args, **kwargs):
        self.cot = get_object_or_404(Cot.objects.select_related("room__floor__section__building__area"), pk=kwargs["cot_id"])
        if self.cot.status != CotStatusChoices.AVAILABLE:
            messages.error(request, "This cot is not available for booking right now.")
            return redirect("public_room_cots", room_id=self.cot.room_id)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        create_public_booking(self.cot, form.cleaned_data)
        messages.success(self.request, "Your booking request has been submitted successfully.")
        return redirect("public_booking_thank_you")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_date = timezone.localdate()
        estimates = estimate_booking_total(self.cot, default_date)
        context.update(
            {
                "page_title": "Book Cot",
                "cot": self.cot,
                "qr_setting": get_active_qr_setting(),
                "estimates": estimates,
            }
        )
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial["booking_from_date"] = timezone.localdate()
        return initial


class BookingThankYouView(TemplateView):
    template_name = "public/thank_you.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Booking Submitted"
        return context


class PublicBillPaymentView(FormView):
    template_name = "public/bill_payment.html"
    form_class = MonthlyRentPaymentForm

    def dispatch(self, request, *args, **kwargs):
        self.bill = get_object_or_404(
            MonthlyRentDue.objects.select_related("student", "booking__cot__room__floor__section__building__area"),
            public_reference=kwargs["reference"],
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        submit_monthly_bill_payment(self.bill, form.cleaned_data)
        messages.success(self.request, "Monthly rent payment submitted for verification.")
        return redirect("public_booking_thank_you")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Pay Monthly Rent",
                "bill": self.bill,
                "qr_setting": get_active_qr_setting(),
            }
        )
        return context
