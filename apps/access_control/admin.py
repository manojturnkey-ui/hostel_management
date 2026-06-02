from django.contrib import admin

from .models import BiometricDevice, GateAccessLog, StudentAccess, StudentAccessHistory


@admin.register(BiometricDevice)
class BiometricDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_name", "device_code", "location", "status", "created_at")
    search_fields = ("device_name", "device_code", "location")
    list_filter = ("status",)


@admin.register(StudentAccess)
class StudentAccessAdmin(admin.ModelAdmin):
    list_display = ("student", "booking", "access_status", "valid_from", "valid_to", "updated_at")
    search_fields = ("student__full_name", "booking__cot__cot_number")
    list_filter = ("access_status",)


@admin.register(StudentAccessHistory)
class StudentAccessHistoryAdmin(admin.ModelAdmin):
    list_display = ("student_access", "previous_status", "new_status", "created_at")
    list_filter = ("new_status", "created_at")


@admin.register(GateAccessLog)
class GateAccessLogAdmin(admin.ModelAdmin):
    list_display = ("student", "device", "access_time", "access_result")
    list_filter = ("access_result", "device")
