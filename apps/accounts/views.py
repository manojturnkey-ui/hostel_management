from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from config.mixins import GuestRequiredMixin
from config.panel_views import PanelTemplateView
from apps.access_control.models import StudentAccess
from apps.bookings.models import BillPaymentStatusChoices, Booking, BookingStatusChoices, MonthlyRentDue
from apps.hostel.models import Area, Building, Cot, CotStatusChoices, Floor, Room, Section
from apps.payments.models import Payment, PaymentStatusChoices

from .forms import GuestAuthenticationForm, GuestPasswordChangeForm, PanelAuthenticationForm


def _selected_int(value):
    return int(value) if value and str(value).isdigit() else None


def _build_cot_cards(queryset):
    cards = []
    for cot in queryset:
        active_booking = None
        for booking in getattr(cot, "dashboard_bookings", []):
            if booking.booking_status == BookingStatusChoices.CONFIRMED:
                active_booking = booking
                break
            if not active_booking:
                active_booking = booking

        theme_map = {
            CotStatusChoices.AVAILABLE: {"class": "cot-available", "badge": "Available"},
            CotStatusChoices.PENDING: {"class": "cot-pending", "badge": "Under Verification"},
            CotStatusChoices.OCCUPIED: {"class": "cot-occupied", "badge": "Occupied"},
            CotStatusChoices.MAINTENANCE: {"class": "cot-maintenance", "badge": "Maintenance"},
            CotStatusChoices.BLOCKED: {"class": "cot-blocked", "badge": "Blocked"},
        }
        theme = theme_map.get(cot.status, {"class": "cot-blocked", "badge": cot.get_status_display()})
        stay_end = active_booking.booking_to_date if active_booking and active_booking.booking_to_date else "Present"

        cards.append(
            {
                "cot": cot,
                "theme": theme["class"],
                "badge": theme["badge"],
                "guest_name": active_booking.student.full_name if active_booking else "",
                "stay_start": active_booking.booking_from_date if active_booking else None,
                "stay_end": stay_end if active_booking else None,
                "status": cot.status,
                "monthly_rent": cot.cot_price,
            }
        )
    return cards


def _build_latest_guest_payment(guest):
    latest_booking_payment = (
        Payment.objects.filter(booking__student=guest)
        .select_related("booking__cot__room__floor__section__building__area")
        .defer(
            "booking__cot__image",
            "booking__cot__room__image",
            "booking__cot__room__floor__image",
            "booking__cot__room__floor__section__image",
            "booking__cot__room__floor__section__building__image",
            "booking__cot__room__floor__section__building__area__image",
            "payment_screenshot",
        )
        .order_by("-confirmed_at", "-created_at")
        .first()
    )
    latest_bill_payment = (
        MonthlyRentDue.objects.filter(student=guest)
        .exclude(payment_status=BillPaymentStatusChoices.UNPAID)
        .select_related("booking__cot__room__floor__section__building__area")
        .defer(
            "booking__cot__image",
            "booking__cot__room__image",
            "booking__cot__room__floor__image",
            "booking__cot__room__floor__section__image",
            "booking__cot__room__floor__section__building__image",
            "booking__cot__room__floor__section__building__area__image",
            "payment_screenshot",
        )
        .order_by("-payment_date", "-confirmed_at", "-updated_at", "-created_at")
        .first()
    )

    def payment_marker(item):
        if not item:
            return timezone.make_aware(datetime(1970, 1, 1))
        return getattr(item, "payment_date", None) or getattr(item, "confirmed_at", None) or item.created_at

    if payment_marker(latest_bill_payment) >= payment_marker(latest_booking_payment):
        if not latest_bill_payment:
            return None
        return {
            "kind": "Monthly Rent",
            "amount": latest_bill_payment.bill_amount,
            "status": latest_bill_payment.payment_status,
            "status_display": latest_bill_payment.get_payment_status_display(),
            "utr": latest_bill_payment.utr_transaction_id,
            "submitted_at": latest_bill_payment.payment_date or latest_bill_payment.created_at,
            "location": latest_bill_payment.booking.cot.get_location_path(),
            "screenshot": latest_bill_payment.payment_screenshot,
        }

    if not latest_booking_payment:
        return None
    return {
        "kind": "Booking Payment",
        "amount": latest_booking_payment.amount,
        "status": latest_booking_payment.payment_status,
        "status_display": latest_booking_payment.get_payment_status_display(),
        "utr": latest_booking_payment.utr_transaction_id,
        "submitted_at": latest_booking_payment.confirmed_at or latest_booking_payment.created_at,
        "location": latest_booking_payment.booking.cot.get_location_path(),
        "screenshot": latest_booking_payment.payment_screenshot,
    }


def _get_booking_bill_context(booking):
    if not booking:
        return None

    today = timezone.localdate()
    prefetched_dues = list(booking.monthly_dues.all())
    dues = sorted(prefetched_dues, key=lambda item: (item.bill_year, item.bill_month, item.created_at), reverse=True)

    current_bill = next((item for item in dues if item.bill_year == today.year and item.bill_month == today.month), None)
    upcoming_or_open_bill = next(
        (
            item
            for item in dues
            if item.payment_status
            in [
                BillPaymentStatusChoices.UNPAID,
                BillPaymentStatusChoices.PENDING_VERIFICATION,
                BillPaymentStatusChoices.OVERDUE,
            ]
        ),
        None,
    )
    selected_bill = current_bill or upcoming_or_open_bill or (dues[0] if dues else None)

    if selected_bill:
        renewal_month = calendar.month_name[selected_bill.bill_month]
        renewal_year = selected_bill.bill_year
        rent_expiry_date = selected_bill.billing_period_end
        blocked_from_date = selected_bill.grace_period_end_date + timedelta(days=1)
    else:
        renewal_month = calendar.month_name[today.month]
        renewal_year = today.year
        month_end = calendar.monthrange(today.year, today.month)[1]
        rent_expiry_date = date(today.year, today.month, month_end)
        blocked_from_date = date(today.year, today.month, 6)

    return {
        "bill": selected_bill,
        "rent_expiry_date": rent_expiry_date,
        "renewal_window_label": f"1 to 5 {renewal_month} {renewal_year}",
        "blocked_from_date": blocked_from_date,
        "blocked_note": (
            f"Please renew your stay between 1 and 5 {renewal_month} {renewal_year}. "
            f"After {blocked_from_date.strftime('%d %b %Y')}, you may not be able to check in until the payment is verified."
        ),
    }


class PanelRootRedirectView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect("panel_dashboard")
            return redirect("guest_dashboard")
        return redirect("panel_login")


class PanelLoginView(LoginView):
    template_name = "admin_panel/accounts/login.html"
    authentication_form = PanelAuthenticationForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect("panel_dashboard")
            return redirect("guest_dashboard")
        return super().dispatch(request, *args, **kwargs)


class PanelLogoutView(LogoutView):
    next_page = reverse_lazy("panel_login")


class DashboardView(PanelTemplateView):
    template_name = "admin_panel/dashboard.html"
    page_title = "Dashboard"
    page_subtitle = "Hostel occupancy, bookings, and payment overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        area_id = _selected_int(self.request.GET.get("area"))
        building_id = _selected_int(self.request.GET.get("building"))
        section_id = _selected_int(self.request.GET.get("section"))
        floor_id = _selected_int(self.request.GET.get("floor"))
        room_id = _selected_int(self.request.GET.get("room"))

        pending_payments = Payment.objects.filter(payment_status=PaymentStatusChoices.PENDING).count()
        pending_bill_payments = MonthlyRentDue.objects.filter(payment_status=BillPaymentStatusChoices.PENDING_VERIFICATION).count()
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
            {"label": "Total Areas", "value": Area.objects.count(), "icon": "iconoir-map", "theme": "sunrise"},
            {"label": "Total Society", "value": Building.objects.count(), "icon": "iconoir-building", "theme": "azure"},
            {"label": "Total Buildings / Wings", "value": Section.objects.count(), "icon": "iconoir-view-columns-3", "theme": "peach"},
            {"label": "Total Floors", "value": Floor.objects.count(), "icon": "iconoir-multiple-pages", "theme": "violet"},
            {"label": "Total Rooms", "value": Room.objects.count(), "icon": "iconoir-home", "theme": "mint"},
            {"label": "Total Cots", "value": Cot.objects.count(), "icon": "iconoir-bed", "theme": "rose"},
            {"label": "Available Cots", "value": Cot.objects.filter(status=CotStatusChoices.AVAILABLE).count(), "icon": "iconoir-check-circle", "theme": "amber"},
            {"label": "Occupied Cots", "value": Cot.objects.filter(status=CotStatusChoices.OCCUPIED).count(), "icon": "iconoir-user", "theme": "ocean"},
            {
                "label": "Pending Bookings",
                "value": Booking.objects.filter(booking_status=BookingStatusChoices.PENDING_ADMIN_CONFIRMATION).count(),
                "icon": "iconoir-clock",
                "theme": "emerald",
            },
            {"label": "Pending Payments", "value": pending_payments + pending_bill_payments, "icon": "iconoir-wallet", "theme": "coral"},
            {
                "label": "Confirmed Bookings",
                "value": Booking.objects.filter(booking_status=BookingStatusChoices.CONFIRMED).count(),
                "icon": "iconoir-check",
                "theme": "sunrise",
            },
            {"label": "Monthly Due Guests", "value": monthly_due_students, "icon": "iconoir-dollar-circle", "theme": "azure"},
        ]

        areas = Area.objects.order_by("area_name")
        buildings = Building.objects.filter(area_id=area_id).order_by("building_name") if area_id else Building.objects.none()
        sections = Section.objects.filter(building_id=building_id).order_by("section_name") if building_id else Section.objects.none()
        floors = Floor.objects.filter(section_id=section_id).order_by("floor_name") if section_id else Floor.objects.none()
        rooms = Room.objects.filter(floor_id=floor_id).order_by("room_number") if floor_id else Room.objects.none()

        cots = Cot.objects.select_related("room__floor__section__building__area").prefetch_related(
            Prefetch(
                "bookings",
                queryset=Booking.objects.filter(
                    booking_status__in=[BookingStatusChoices.PENDING_ADMIN_CONFIRMATION, BookingStatusChoices.CONFIRMED]
                )
                .select_related("student")
                .order_by("-confirmed_at", "-created_at"),
                to_attr="dashboard_bookings",
            )
        )
        if area_id:
            cots = cots.filter(room__floor__section__building__area_id=area_id)
        if building_id:
            cots = cots.filter(room__floor__section__building_id=building_id)
        if section_id:
            cots = cots.filter(room__floor__section_id=section_id)
        if floor_id:
            cots = cots.filter(room__floor_id=floor_id)
        if room_id:
            cots = cots.filter(room_id=room_id)

        cots = cots.order_by(
            "room__floor__section__building__area__area_name",
            "room__floor__section__building__building_name",
            "room__floor__section__section_name",
            "room__floor__floor_name",
            "room__room_number",
            "cot_number",
        )

        context["hostel_filters"] = {
            "areas": areas,
            "buildings": buildings,
            "sections": sections,
            "floors": floors,
            "rooms": rooms,
            "selected": {
                "area": area_id,
                "building": building_id,
                "section": section_id,
                "floor": floor_id,
                "room": room_id,
            },
        }
        context["cot_cards"] = _build_cot_cards(cots)
        return context


class GuestLoginView(LoginView):
    template_name = "public/guest_login.html"
    authentication_form = GuestAuthenticationForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect("panel_dashboard")
            return redirect("guest_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("guest_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Guest Login",
                "page_description": "Sign in to review your booking request, stay details, and latest payment.",
            }
        )
        return context


class GuestLogoutView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been signed out from the guest portal.")
        return redirect("guest_login")


class GuestDashboardView(GuestRequiredMixin, TemplateView):
    template_name = "public/guest_dashboard.html"

    def _sync_guest_username(self, guest):
        desired_username = guest.mobile_number
        user = self.request.user
        if not desired_username or user.username == desired_username:
            return desired_username or user.username

        User = get_user_model()
        existing_owner = User.objects.filter(username=desired_username).exclude(pk=user.pk).first()
        if existing_owner:
            return user.username

        user.username = desired_username
        user.mobile_number = guest.mobile_number
        user.save(update_fields=["username", "mobile_number"])
        return desired_username

    def post(self, request, *args, **kwargs):
        password_form = GuestPasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your guest portal password has been updated.")
            return redirect(f"{reverse_lazy('guest_dashboard')}#guest-change-password")
        context = self.get_context_data(
            password_form=password_form,
            active_guest_section="guest-change-password-panel",
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guest = self.request.user.guest_profile
        guest_login_name = self._sync_guest_username(guest)
        bookings = list(
            guest.bookings.select_related("cot__room__floor__section__building__area", "payment", "student_access")
            .prefetch_related("monthly_dues")
            .defer(
                "cot__image",
                "cot__room__image",
                "cot__room__floor__image",
                "cot__room__floor__section__image",
                "cot__room__floor__section__building__image",
                "cot__room__floor__section__building__area__image",
                "payment__payment_screenshot",
            )
            .order_by("-created_at")
        )
        pending_dashboard_booking = next(
            (item for item in bookings if item.booking_status == BookingStatusChoices.PENDING_ADMIN_CONFIRMATION),
            None,
        )
        current_booking = next((item for item in bookings if item.booking_status == BookingStatusChoices.CONFIRMED), None)
        latest_verified_booking = next(
            (item for item in bookings if item.booking_status != BookingStatusChoices.PENDING_ADMIN_CONFIRMATION),
            None,
        )
        booking_status_booking = current_booking or latest_verified_booking
        excluded_booking_ids = {
            booking.pk for booking in [pending_dashboard_booking, booking_status_booking] if booking is not None
        }
        booking_history = [booking for booking in bookings if booking.pk not in excluded_booking_ids]
        current_access = None
        if booking_status_booking and booking_status_booking.booking_status == BookingStatusChoices.CONFIRMED:
            try:
                current_access = booking_status_booking.student_access
            except StudentAccess.DoesNotExist:
                current_access = None

        dashboard_current_booking = current_booking or booking_status_booking
        dashboard_current_booking_billing = _get_booking_bill_context(dashboard_current_booking)
        booking_status_billing = _get_booking_bill_context(booking_status_booking)

        context.update(
            {
                "page_title": "Guest Portal",
                "page_description": "Track your booking status, stay details, and latest payment in one place.",
                "guest": guest,
                "guest_bookings": bookings,
                "dashboard_pending_booking": pending_dashboard_booking,
                "dashboard_current_booking": dashboard_current_booking,
                "dashboard_current_booking_billing": dashboard_current_booking_billing,
                "booking_status_booking": booking_status_booking,
                "booking_status_billing": booking_status_billing,
                "booking_history": booking_history,
                "current_access": current_access,
                "latest_payment": _build_latest_guest_payment(guest),
                "guest_login_name": guest_login_name,
                "password_form": kwargs.get("password_form") or GuestPasswordChangeForm(user=self.request.user),
                "active_guest_section": kwargs.get("active_guest_section", "guest-dashboard-panel"),
            }
        )
        return context


class GuestPasswordChangeView(GuestRequiredMixin, PasswordChangeView):
    template_name = "public/guest_change_password.html"
    form_class = GuestPasswordChangeForm
    success_url = reverse_lazy("guest_dashboard")

    def dispatch(self, request, *args, **kwargs):
        return redirect(f"{reverse_lazy('guest_dashboard')}#guest-change-password")

    def form_valid(self, form):
        messages.success(self.request, "Your guest portal password has been updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Change Password",
                "page_description": "Keep your guest portal credentials secure.",
            }
        )
        return context
