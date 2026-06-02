from django.contrib import admin

from .models import Area, Building, Cot, ExcelUploadLog, Floor, Room, Section, SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("site_title", "billing_calculation_method", "payment_window_end_day", "grace_period_days")


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("area_name", "status", "created_at")
    search_fields = ("area_name",)
    list_filter = ("status",)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("building_name", "area", "status", "created_at")
    search_fields = ("building_name", "area__area_name")
    list_filter = ("status", "area")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("section_name", "building", "status", "created_at")
    search_fields = ("section_name", "building__building_name")
    list_filter = ("status", "building")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("floor_name", "section", "status", "created_at")
    search_fields = ("floor_name", "section__section_name")
    list_filter = ("status", "section")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "floor", "room_name", "room_type", "status")
    search_fields = ("room_number", "room_name", "floor__floor_name")
    list_filter = ("status", "room_type")


@admin.register(Cot)
class CotAdmin(admin.ModelAdmin):
    list_display = ("cot_number", "room", "cot_price", "security_deposit", "status")
    search_fields = ("cot_number", "room__room_number")
    list_filter = ("status",)


@admin.register(ExcelUploadLog)
class ExcelUploadLogAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_by", "total_rows", "success_count", "failure_count", "status", "created_at")
    list_filter = ("status", "created_at")
