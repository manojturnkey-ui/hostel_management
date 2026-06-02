from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Additional Info", {"fields": ("display_name", "mobile_number")}),)
    list_display = ("username", "email", "display_name", "is_staff", "is_active")
