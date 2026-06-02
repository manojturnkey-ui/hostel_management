from django.contrib import admin

from .models import Payment, QRCodeSetting


@admin.register(QRCodeSetting)
class QRCodeSettingAdmin(admin.ModelAdmin):
    list_display = ("title", "upi_id", "account_name", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "payment_method", "payment_status", "created_at")
    search_fields = ("booking__student__full_name", "utr_transaction_id")
    list_filter = ("payment_status", "payment_method", "created_at")
