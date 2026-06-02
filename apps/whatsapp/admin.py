from django.contrib import admin

from .models import WhatsAppLog, WhatsAppMessageTemplate, WhatsAppSetting


@admin.register(WhatsAppSetting)
class WhatsAppSettingAdmin(admin.ModelAdmin):
    list_display = ("provider", "instance_id", "phone_number_id", "is_active", "created_at")
    list_filter = ("provider", "is_active")


@admin.register(WhatsAppMessageTemplate)
class WhatsAppMessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_key", "title", "is_active", "created_at")
    search_fields = ("template_key", "title")
    list_filter = ("is_active",)


@admin.register(WhatsAppLog)
class WhatsAppLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "mobile_number", "status", "created_at")
    search_fields = ("mobile_number", "event_type", "message")
    list_filter = ("status", "event_type")
