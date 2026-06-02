from __future__ import annotations

from typing import Any


def panel_context(request) -> dict[str, Any]:
    panel_menu = [
        {"label": "Dashboard", "icon": "iconoir-report-columns", "url_name": "panel_dashboard"},
        {
            "label": "Hostel Setup",
            "icon": "iconoir-building",
            "children": [
                {"label": "Areas", "url_name": "panel_area_list"},
                {"label": "Buildings", "url_name": "panel_building_list"},
                {"label": "Sections / Wings", "url_name": "panel_section_list"},
                {"label": "Floors", "url_name": "panel_floor_list"},
                {"label": "Rooms", "url_name": "panel_room_list"},
                {"label": "Cots", "url_name": "panel_cot_list"},
                {"label": "Excel Upload", "url_name": "panel_excel_upload"},
            ],
        },
        {
            "label": "Bookings",
            "icon": "iconoir-book",
            "children": [
                {"label": "Pending Bookings", "url_name": "panel_pending_booking_list"},
                {"label": "Confirmed Bookings", "url_name": "panel_confirmed_booking_list"},
                {"label": "Rejected Bookings", "url_name": "panel_rejected_booking_list"},
            ],
        },
        {
            "label": "Payments",
            "icon": "iconoir-wallet",
            "children": [
                {"label": "Pending Verification", "url_name": "panel_pending_payment_list"},
                {"label": "Payment History", "url_name": "panel_payment_history"},
            ],
        },
        {"label": "Students", "icon": "iconoir-user", "url_name": "panel_student_list"},
        {"label": "QR Settings", "icon": "iconoir-qr-code", "url_name": "panel_qr_setting_list"},
        {
            "label": "WhatsApp Settings",
            "icon": "iconoir-chat-bubble",
            "children": [
                {"label": "WhatsApp Scan", "url_name": "panel_whatsapp_scan"},
                {"label": "WhatsApp Template", "url_name": "panel_whatsapp_template_list"},
            ],
        },
        {
            "label": "Rent Management",
            "icon": "iconoir-dollar-circle",
            "children": [
                {"label": "Current Month Bills", "url_name": "panel_current_bill_list"},
                {"label": "Pending Verification", "url_name": "panel_pending_bill_list"},
                {"label": "Paid Bills", "url_name": "panel_paid_bill_list"},
                {"label": "Unpaid Bills", "url_name": "panel_unpaid_bill_list"},
                {"label": "Overdue Bills", "url_name": "panel_overdue_bill_list"},
                {"label": "Student Ledger", "url_name": "panel_student_ledger"},
                {"label": "Manual Bill Generate", "url_name": "panel_manual_bill_generate"},
                {"label": "Manual Grace Extension", "url_name": "panel_manual_grace_extension"},
            ],
        },
        {
            "label": "Access Control",
            "icon": "iconoir-fingerprint-lock-circle",
            "children": [
                {"label": "Student Access", "url_name": "panel_student_access_list"},
                {"label": "Biometric Devices", "url_name": "panel_biometric_device_list"},
                {"label": "Gate Logs", "url_name": "panel_gate_access_log_list"},
            ],
        },
        {"label": "Reports", "icon": "iconoir-pie-chart", "url_name": "panel_reports_home"},
        {"label": "Settings", "icon": "iconoir-settings", "url_name": "panel_system_settings"},
    ]

    site_title = "Hostel Management"
    try:
        from apps.hostel.models import SystemSetting

        system_setting = SystemSetting.get_solo()
        if system_setting and system_setting.site_title:
            site_title = system_setting.site_title
    except Exception:
        pass

    return {"panel_menu": panel_menu, "panel_site_title": site_title}
