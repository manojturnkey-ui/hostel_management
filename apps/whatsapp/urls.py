from django.urls import path

from .views import (
    WhatsAppGatewayLogoutView,
    WhatsAppGatewayRestartView,
    WhatsAppRootRedirectView,
    WhatsAppScanStatusView,
    WhatsAppScanView,
    WhatsAppTemplateCreateView,
    WhatsAppTemplateListView,
    WhatsAppTemplateUpdateView,
)


urlpatterns = [
    path("whatsapp/", WhatsAppRootRedirectView.as_view(), name="panel_whatsapp_settings"),
    path("whatsapp/scan/", WhatsAppScanView.as_view(), name="panel_whatsapp_scan"),
    path("whatsapp/scan/status/", WhatsAppScanStatusView.as_view(), name="panel_whatsapp_scan_status"),
    path("whatsapp/restart/", WhatsAppGatewayRestartView.as_view(), name="panel_whatsapp_restart"),
    path("whatsapp/logout/", WhatsAppGatewayLogoutView.as_view(), name="panel_whatsapp_logout"),
    path("whatsapp/templates/", WhatsAppTemplateListView.as_view(), name="panel_whatsapp_template_list"),
    path("whatsapp/templates/add/", WhatsAppTemplateCreateView.as_view(), name="panel_whatsapp_template_create"),
    path("whatsapp/templates/<int:pk>/edit/", WhatsAppTemplateUpdateView.as_view(), name="panel_whatsapp_template_update"),
]
