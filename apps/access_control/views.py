from django.urls import reverse_lazy

from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView

from .forms import BiometricDeviceForm, StudentAccessForm
from .models import BiometricDevice, GateAccessLog, StudentAccess


class StudentAccessListView(PanelListView):
    model = StudentAccess
    page_title = "Guest Access"
    page_subtitle = "Manual gate access control and current status"
    update_url_name = "panel_student_access_update"
    columns = [
        {"label": "Guest", "value": "student.full_name"},
        {"label": "Room", "value": "booking.cot.room.room_number"},
        {"label": "Cot", "value": "booking.cot.cot_number"},
        {"label": "Status", "value": "access_status"},
        {"label": "Reason", "value": "reason"},
        {"label": "Updated", "value": "updated_at"},
    ]
    search_fields = ["student__full_name", "booking__cot__room__room_number", "booking__cot__cot_number", "reason"]


class StudentAccessUpdateView(PanelUpdateView):
    model = StudentAccess
    form_class = StudentAccessForm
    page_title = "Update Guest Access"
    back_url_name = "panel_student_access_list"
    success_message = "Guest access updated successfully."
    success_url = reverse_lazy("panel_student_access_list")


class BiometricDeviceListView(PanelListView):
    model = BiometricDevice
    page_title = "Biometric Devices"
    page_subtitle = "Future-ready device records for gate hardware integration"
    create_url_name = "panel_biometric_device_create"
    update_url_name = "panel_biometric_device_update"
    columns = [
        {"label": "Device Name", "value": "device_name"},
        {"label": "Code", "value": "device_code"},
        {"label": "Location", "value": "location"},
        {"label": "IP Address", "value": "ip_address"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["device_name", "device_code", "location", "ip_address"]


class BiometricDeviceCreateView(PanelCreateView):
    model = BiometricDevice
    form_class = BiometricDeviceForm
    page_title = "Create Biometric Device"
    back_url_name = "panel_biometric_device_list"
    success_message = "Biometric device created successfully."
    success_url = reverse_lazy("panel_biometric_device_list")


class BiometricDeviceUpdateView(PanelUpdateView):
    model = BiometricDevice
    form_class = BiometricDeviceForm
    page_title = "Update Biometric Device"
    back_url_name = "panel_biometric_device_list"
    success_message = "Biometric device updated successfully."
    success_url = reverse_lazy("panel_biometric_device_list")


class GateAccessLogListView(PanelListView):
    model = GateAccessLog
    page_title = "Gate Access Logs"
    page_subtitle = "Allowed and denied gate transactions"
    columns = [
        {"label": "Guest", "value": "student.full_name"},
        {"label": "Device", "value": "device.device_name"},
        {"label": "Access Time", "value": "access_time"},
        {"label": "Result", "value": "access_result"},
        {"label": "Reason", "value": "reason"},
    ]
    search_fields = ["student__full_name", "device__device_name", "reason", "raw_response"]
