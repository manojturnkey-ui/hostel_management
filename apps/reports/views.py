from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.access_control.models import GateAccessLog, StudentAccess
from config.mixins import PanelLoginRequiredMixin
from apps.bookings.models import BillPaymentStatusChoices, Booking, BookingStatusChoices, MonthlyRentDue, Student
from apps.hostel.models import Cot, CotStatusChoices
from apps.payments.models import Payment

from .forms import ReportFilterForm
from .services import export_rows_to_excel


class ReportsHomeView(PanelLoginRequiredMixin, TemplateView):
    template_name = "admin_panel/reports/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Reports",
                "page_subtitle": "Operational exports and occupancy analytics",
                "report_links": [
                    {"key": "available-cots", "label": "Available Cots"},
                    {"key": "occupied-cots", "label": "Occupied Cots"},
                    {"key": "pending-bookings", "label": "Pending Bookings"},
                    {"key": "payments", "label": "Payment Report"},
                    {"key": "students", "label": "Student Report"},
                    {"key": "monthly-dues", "label": "Monthly Due Report"},
                    {"key": "monthly-rent-collection", "label": "Monthly Rent Collection"},
                    {"key": "pending-rent", "label": "Pending Rent Report"},
                    {"key": "overdue-rent", "label": "Overdue Rent Report"},
                    {"key": "blocked-access", "label": "Blocked Access Report"},
                    {"key": "dues-by-location", "label": "Area / Society / Room Wise Dues"},
                    {"key": "occupancy", "label": "Area / Society / Room Occupancy"},
                ],
            }
        )
        return context


class ReportResultView(PanelLoginRequiredMixin, TemplateView):
    template_name = "admin_panel/reports/results.html"

    def apply_common_filters(self, queryset, prefix: str):
        data = self.filter_form.cleaned_data
        if data.get("area"):
            queryset = queryset.filter(**{f"{prefix}room__floor__section__building__area": data["area"]})
        if data.get("building"):
            queryset = queryset.filter(**{f"{prefix}room__floor__section__building": data["building"]})
        if data.get("section"):
            queryset = queryset.filter(**{f"{prefix}room__floor__section": data["section"]})
        if data.get("floor"):
            queryset = queryset.filter(**{f"{prefix}room__floor": data["floor"]})
        if data.get("room"):
            queryset = queryset.filter(**{f"{prefix}room": data["room"]})
        return queryset

    def apply_status_filter(self, queryset, field_name: str):
        status = self.filter_form.cleaned_data.get("status")
        if status:
            queryset = queryset.filter(**{field_name: status})
        return queryset

    def apply_date_filter(self, queryset, field_name: str):
        date_from = self.filter_form.cleaned_data.get("date_from")
        date_to = self.filter_form.cleaned_data.get("date_to")
        if date_from:
            queryset = queryset.filter(**{f"{field_name}__date__gte": date_from})
        if date_to:
            queryset = queryset.filter(**{f"{field_name}__date__lte": date_to})
        return queryset

    def get_report_config(self):
        report_key = self.kwargs["report_key"]
        today = timezone.localdate()
        if report_key == "available-cots":
            queryset = self.apply_common_filters(
                Cot.objects.filter(status=CotStatusChoices.AVAILABLE).select_related("room__floor__section__building__area"),
                "",
            )
            queryset = self.apply_status_filter(queryset, "status")
            return "Available Cots", ["Area", "Society", "Room", "Cot", "Price", "Status"], [
                [
                    cot.room.floor.section.building.area.area_name,
                    cot.room.floor.section.building.building_name,
                    cot.room.room_number,
                    cot.cot_number,
                    cot.cot_price,
                    cot.status,
                ]
                for cot in queryset
            ]
        if report_key == "occupied-cots":
            queryset = self.apply_common_filters(
                Cot.objects.filter(status=CotStatusChoices.OCCUPIED).select_related("room__floor__section__building__area"),
                "",
            )
            queryset = self.apply_status_filter(queryset, "status")
            return "Occupied Cots", ["Area", "Society", "Room", "Cot", "Occupant", "Status"], [
                [
                    cot.room.floor.section.building.area.area_name,
                    cot.room.floor.section.building.building_name,
                    cot.room.room_number,
                    cot.cot_number,
                    cot.current_student_name(),
                    cot.status,
                ]
                for cot in queryset
            ]
        if report_key == "pending-bookings":
            queryset = self.apply_common_filters(
                Booking.objects.filter(booking_status=BookingStatusChoices.PENDING_ADMIN_CONFIRMATION).select_related("student", "cot__room__floor__section__building__area"),
                "cot__",
            )
            queryset = self.apply_status_filter(queryset, "booking_status")
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Pending Bookings", ["Student", "Mobile", "Room", "Cot", "Amount", "Created"], [
                [
                    booking.student.full_name,
                    booking.student.mobile_number,
                    booking.cot.room.room_number,
                    booking.cot.cot_number,
                    booking.total_amount,
                    booking.created_at.strftime("%Y-%m-%d %H:%M"),
                ]
                for booking in queryset
            ]
        if report_key == "payments":
            queryset = self.apply_common_filters(
                Payment.objects.select_related("booking__student", "booking__cot__room__floor__section__building__area"),
                "booking__cot__",
            )
            queryset = self.apply_status_filter(queryset, "payment_status")
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Payment Report", ["Student", "Room", "Cot", "Amount", "UTR", "Status", "Created"], [
                [
                    payment.booking.student.full_name,
                    payment.booking.cot.room.room_number,
                    payment.booking.cot.cot_number,
                    payment.amount,
                    payment.utr_transaction_id,
                    payment.payment_status,
                    timezone.localtime(payment.created_at).strftime("%Y-%m-%d %H:%M"),
                ]
                for payment in queryset
            ]
        if report_key == "students":
            queryset = Student.objects.all()
            if self.filter_form.cleaned_data.get("area"):
                queryset = queryset.filter(bookings__cot__room__floor__section__building__area=self.filter_form.cleaned_data["area"]).distinct()
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Student Report", ["Student", "Mobile", "WhatsApp", "City / Village", "State"], [
                [student.full_name, student.mobile_number, student.whatsapp_number, student.city_village, student.state]
                for student in queryset
            ]
        if report_key == "monthly-dues":
            queryset = MonthlyRentDue.objects.filter(
                bill_month=today.month,
                bill_year=today.year,
                payment_status__in=[
                    BillPaymentStatusChoices.UNPAID,
                    BillPaymentStatusChoices.PENDING_VERIFICATION,
                    BillPaymentStatusChoices.OVERDUE,
                ],
            ).select_related("student", "booking__cot__room__floor__section__building__area")
            queryset = self.apply_common_filters(queryset, "booking__cot__")
            queryset = self.apply_status_filter(queryset, "payment_status")
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Monthly Due Report", ["Student", "Room", "Cot", "Bill Amount", "Status", "Grace End"], [
                [
                    bill.student.full_name,
                    bill.booking.cot.room.room_number,
                    bill.booking.cot.cot_number,
                    bill.bill_amount,
                    bill.payment_status,
                    bill.grace_period_end_date,
                ]
                for bill in queryset
            ]
        if report_key == "monthly-rent-collection":
            queryset = MonthlyRentDue.objects.filter(payment_status=BillPaymentStatusChoices.PAID).select_related(
                "student",
                "booking__cot__room__floor__section__building__area",
            )
            queryset = self.apply_common_filters(queryset, "booking__cot__")
            queryset = self.apply_status_filter(queryset, "payment_status")
            queryset = self.apply_date_filter(queryset, "payment_date")
            return "Monthly Rent Collection Report", ["Student", "Room", "Cot", "Bill Amount", "Payment Date", "UTR"], [
                [
                    bill.student.full_name,
                    bill.booking.cot.room.room_number,
                    bill.booking.cot.cot_number,
                    bill.bill_amount,
                    bill.payment_date.strftime("%Y-%m-%d %H:%M") if bill.payment_date else "-",
                    bill.utr_transaction_id,
                ]
                for bill in queryset
            ]
        if report_key == "pending-rent":
            queryset = MonthlyRentDue.objects.filter(
                payment_status__in=[BillPaymentStatusChoices.UNPAID, BillPaymentStatusChoices.PENDING_VERIFICATION]
            ).select_related("student", "booking__cot__room__floor__section__building__area")
            queryset = self.apply_common_filters(queryset, "booking__cot__")
            queryset = self.apply_status_filter(queryset, "payment_status")
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Pending Rent Report", ["Student", "Room", "Cot", "Bill Amount", "Status", "Grace End"], [
                [
                    bill.student.full_name,
                    bill.booking.cot.room.room_number,
                    bill.booking.cot.cot_number,
                    bill.bill_amount,
                    bill.payment_status,
                    bill.grace_period_end_date,
                ]
                for bill in queryset
            ]
        if report_key == "overdue-rent":
            queryset = MonthlyRentDue.objects.filter(payment_status=BillPaymentStatusChoices.OVERDUE).select_related(
                "student",
                "booking__cot__room__floor__section__building__area",
            )
            queryset = self.apply_common_filters(queryset, "booking__cot__")
            queryset = self.apply_status_filter(queryset, "payment_status")
            queryset = self.apply_date_filter(queryset, "created_at")
            return "Overdue Rent Report", ["Student", "Room", "Cot", "Bill Amount", "Grace End", "Remark"], [
                [
                    bill.student.full_name,
                    bill.booking.cot.room.room_number,
                    bill.booking.cot.cot_number,
                    bill.bill_amount,
                    bill.grace_period_end_date,
                    bill.admin_remark or "-",
                ]
                for bill in queryset
            ]
        if report_key == "blocked-access":
            queryset = StudentAccess.objects.filter(access_status="blocked").select_related(
                "student",
                "booking__cot__room__floor__section__building__area",
            )
            queryset = self.apply_common_filters(queryset, "booking__cot__")
            queryset = self.apply_status_filter(queryset, "access_status")
            queryset = self.apply_date_filter(queryset, "updated_at")
            return "Blocked Access Report", ["Student", "Room", "Cot", "Status", "Reason", "Updated"], [
                [
                    access.student.full_name,
                    access.booking.cot.room.room_number,
                    access.booking.cot.cot_number,
                    access.access_status,
                    access.reason,
                    timezone.localtime(access.updated_at).strftime("%Y-%m-%d %H:%M"),
                ]
                for access in queryset
            ]
        if report_key == "dues-by-location":
            dues_queryset = MonthlyRentDue.objects.filter(
                payment_status__in=[
                    BillPaymentStatusChoices.UNPAID,
                    BillPaymentStatusChoices.PENDING_VERIFICATION,
                    BillPaymentStatusChoices.OVERDUE,
                ]
            )
            dues_queryset = self.apply_common_filters(dues_queryset, "booking__cot__")
            dues_queryset = self.apply_status_filter(dues_queryset, "payment_status")
            dues = (
                dues_queryset.values(
                    "booking__cot__room__floor__section__building__area__area_name",
                    "booking__cot__room__floor__section__building__building_name",
                    "booking__cot__room__room_number",
                )
                .annotate(due_count=Count("id"), total_due_amount=Sum("bill_amount"))
                .order_by(
                    "booking__cot__room__floor__section__building__area__area_name",
                    "booking__cot__room__floor__section__building__building_name",
                    "booking__cot__room__room_number",
                )
            )
            return "Area / Society / Room Wise Dues Report", ["Area", "Society", "Room", "Due Count", "Due Amount"], [
                [
                    row["booking__cot__room__floor__section__building__area__area_name"],
                    row["booking__cot__room__floor__section__building__building_name"],
                    row["booking__cot__room__room_number"],
                    row["due_count"],
                    row["total_due_amount"],
                ]
                for row in dues
            ]
        occupancy_queryset = self.apply_common_filters(
            Booking.objects.filter(booking_status=BookingStatusChoices.CONFIRMED),
            "cot__",
        )
        occupancy_queryset = self.apply_status_filter(occupancy_queryset, "booking_status")
        occupancy_queryset = self.apply_date_filter(occupancy_queryset, "created_at")
        occupancy = (
            occupancy_queryset
            .values(
                "cot__room__floor__section__building__area__area_name",
                "cot__room__floor__section__building__building_name",
                "cot__room__room_number",
            )
            .annotate(total=Count("id"))
            .order_by("cot__room__floor__section__building__area__area_name", "cot__room__room_number")
        )
        return "Occupancy Report", ["Area", "Society", "Room", "Occupied Count"], [
            [
                row["cot__room__floor__section__building__area__area_name"],
                row["cot__room__floor__section__building__building_name"],
                row["cot__room__room_number"],
                row["total"],
            ]
            for row in occupancy
        ]

    def get(self, request, *args, **kwargs):
        self.filter_form = ReportFilterForm(request.GET)
        self.filter_form.is_valid()
        title, headers, rows = self.get_report_config()
        if request.GET.get("export") == "xlsx":
            return export_rows_to_excel(f"{self.kwargs['report_key']}.xlsx", headers, rows)
        export_query = request.GET.copy()
        export_query.pop("export", None)
        context = self.get_context_data(
            page_title=title,
            page_subtitle="Filtered report results",
            report_headers=headers,
            report_rows=rows,
            filter_form=self.filter_form,
            report_key=self.kwargs["report_key"],
            export_query=export_query.urlencode(),
        )
        return self.render_to_response(context)
