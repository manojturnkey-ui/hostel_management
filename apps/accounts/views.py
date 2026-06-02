from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View

from config.panel_views import PanelTemplateView
from apps.access_control.models import StudentAccess
from apps.bookings.models import BillPaymentStatusChoices, Booking, BookingStatusChoices, MonthlyRentDue
from apps.hostel.models import Area, Building, Cot, CotStatusChoices, Room
from apps.payments.models import Payment, PaymentStatusChoices

from .forms import PanelAuthenticationForm


class PanelRootRedirectView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("panel_dashboard")
        return redirect("panel_login")


class PanelLoginView(LoginView):
    template_name = "admin_panel/accounts/login.html"
    authentication_form = PanelAuthenticationForm
    redirect_authenticated_user = True


class PanelLogoutView(LogoutView):
    next_page = reverse_lazy("panel_login")


class DashboardView(PanelTemplateView):
    template_name = "admin_panel/dashboard.html"
    page_title = "Dashboard"
    page_subtitle = "Hostel occupancy, bookings, and payment overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        pending_payments = Payment.objects.filter(payment_status=PaymentStatusChoices.PENDING).count()
        pending_bill_payments = MonthlyRentDue.objects.filter(
            payment_status=BillPaymentStatusChoices.PENDING_VERIFICATION
        ).count()
        monthly_due_students = (
            MonthlyRentDue.objects.filter(
                bill_month=today.month,
                bill_year=today.year,
                payment_status__in=[
                    BillPaymentStatusChoices.UNPAID,
                    BillPaymentStatusChoices.PENDING_VERIFICATION,
                    BillPaymentStatusChoices.OVERDUE,
                ],
            )
            .values("student_id")
            .distinct()
            .count()
        )
        context["dashboard_cards"] = [
            {"label": "Total Areas", "value": Area.objects.count(), "icon": "iconoir-map"},
            {"label": "Total Buildings", "value": Building.objects.count(), "icon": "iconoir-building"},
            {"label": "Total Rooms", "value": Room.objects.count(), "icon": "iconoir-home"},
            {"label": "Total Cots", "value": Cot.objects.count(), "icon": "iconoir-bed"},
            {"label": "Available Cots", "value": Cot.objects.filter(status=CotStatusChoices.AVAILABLE).count(), "icon": "iconoir-check-circle"},
            {"label": "Occupied Cots", "value": Cot.objects.filter(status=CotStatusChoices.OCCUPIED).count(), "icon": "iconoir-user"},
            {"label": "Pending Bookings", "value": Booking.objects.filter(booking_status=BookingStatusChoices.PENDING_ADMIN_CONFIRMATION).count(), "icon": "iconoir-clock"},
            {"label": "Pending Payments", "value": pending_payments + pending_bill_payments, "icon": "iconoir-wallet"},
            {"label": "Confirmed Bookings", "value": Booking.objects.filter(booking_status=BookingStatusChoices.CONFIRMED).count(), "icon": "iconoir-check"},
            {"label": "Monthly Due Students", "value": monthly_due_students, "icon": "iconoir-dollar-circle"},
        ]
        context["recent_bookings"] = Booking.objects.select_related("student", "cot").order_by("-created_at")[:8]
        context["access_overview"] = StudentAccess.objects.select_related("student").order_by("-updated_at")[:8]
        return context
