from django.contrib import admin

from .models import Booking, MonthlyRentDue, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "mobile_number", "whatsapp_number", "city_village", "created_at")
    search_fields = ("full_name", "mobile_number", "whatsapp_number")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("student", "cot", "booking_from_date", "monthly_rent", "booking_status", "created_at")
    search_fields = ("student__full_name", "student__mobile_number", "cot__cot_number", "cot__room__room_number")
    list_filter = ("booking_status", "booking_from_date", "created_at")


@admin.register(MonthlyRentDue)
class MonthlyRentDueAdmin(admin.ModelAdmin):
    list_display = ("student", "bill_month", "bill_year", "bill_amount", "payment_status", "grace_period_end_date")
    search_fields = ("student__full_name", "utr_transaction_id")
    list_filter = ("payment_status", "bill_month", "bill_year")
