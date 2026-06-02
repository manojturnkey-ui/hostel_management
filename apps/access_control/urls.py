from django.urls import path

from .views import (
    BiometricDeviceCreateView,
    BiometricDeviceListView,
    BiometricDeviceUpdateView,
    GateAccessLogListView,
    StudentAccessListView,
    StudentAccessUpdateView,
)


urlpatterns = [
    path("access-control/", StudentAccessListView.as_view(), name="panel_student_access_list"),
    path("access-control/student-access/<int:pk>/edit/", StudentAccessUpdateView.as_view(), name="panel_student_access_update"),
    path("access-control/devices/", BiometricDeviceListView.as_view(), name="panel_biometric_device_list"),
    path("access-control/devices/add/", BiometricDeviceCreateView.as_view(), name="panel_biometric_device_create"),
    path("access-control/devices/<int:pk>/edit/", BiometricDeviceUpdateView.as_view(), name="panel_biometric_device_update"),
    path("access-control/logs/", GateAccessLogListView.as_view(), name="panel_gate_access_log_list"),
]
