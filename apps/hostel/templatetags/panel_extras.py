from datetime import date, datetime
from decimal import Decimal

from django import template
from django.utils import timezone


register = template.Library()


@register.filter
def get_attr(obj, attr_path):
    value = obj
    for part in attr_path.split("."):
        if value is None:
            return ""
        value = getattr(value, part, "")
        if callable(value):
            value = value()
    return value


@register.filter
def display_value(value):
    if value in [None, ""]:
        return "-"
    if isinstance(value, bool):
        return "Active" if value else "Inactive"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value


@register.filter
def badge_class(value):
    if isinstance(value, bool):
        return "success" if value else "secondary"
    mapping = {
        "active": "success",
        "inactive": "secondary",
        "available": "success",
        "pending": "warning",
        "occupied": "danger",
        "maintenance": "secondary",
        "blocked": "dark",
        "confirmed": "success",
        "rejected": "danger",
        "cancelled": "secondary",
        "expired": "dark",
        "vacated": "info",
        "paid": "success",
        "pending_verification": "warning",
        "unpaid": "secondary",
        "overdue": "danger",
        "allowed": "success",
        "denied": "danger",
        "sent": "success",
        "failed": "danger",
    }
    return mapping.get(str(value).lower(), "primary")


@register.filter
def dict_get(value, key):
    if isinstance(value, dict):
        return value.get(key, [])
    return []


@register.simple_tag
def menu_group_open(group, current_name):
    for child in group.get("children", []):
        if child.get("url_name") == current_name:
            return "show"
    return ""


@register.simple_tag
def menu_group_active(group, current_name):
    for child in group.get("children", []):
        if child.get("url_name") == current_name:
            return "active"
    return ""
