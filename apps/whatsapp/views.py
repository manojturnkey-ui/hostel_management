from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import RedirectView, TemplateView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView

from .forms import WhatsAppMessageTemplateForm
from .models import WhatsAppLog, WhatsAppMessageTemplate
from .services import (
    ensure_default_templates,
    fetch_gateway_qr,
    fetch_gateway_status,
    get_active_setting,
    logout_gateway_session,
    restart_gateway_session,
)


class WhatsAppRootRedirectView(PanelLoginRequiredMixin, RedirectView):
    pattern_name = "panel_whatsapp_scan"
    permanent = False


class WhatsAppScanView(PanelLoginRequiredMixin, TemplateView):
    template_name = "admin_panel/whatsapp/scan.html"

    def dispatch(self, request, *args, **kwargs):
        ensure_default_templates()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_setting = get_active_setting()
        gateway_status = fetch_gateway_status(active_setting)
        gateway_qr_image_data_url = ""
        gateway_qr_message = ""
        if gateway_status.configured and gateway_status.reachable and not gateway_status.connected:
            qr_response = fetch_gateway_qr(active_setting)
            if qr_response.ok:
                gateway_qr_image_data_url = qr_response.data.get("qrImageDataUrl", "") or ""
                gateway_qr_message = qr_response.data.get("message", "") or ""
            else:
                gateway_qr_message = qr_response.summary

        context.update(
            {
                "page_title": "WhatsApp Scan",
                "page_subtitle": "QR connect, live connection status, and recent delivery logs",
                "recent_logs": WhatsAppLog.objects.select_related("student").order_by("-created_at")[:20],
                "gateway_status": gateway_status,
                "gateway_qr_image_data_url": gateway_qr_image_data_url,
                "gateway_qr_message": gateway_qr_message,
            }
        )
        return context


class WhatsAppScanStatusView(PanelLoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        active_setting = get_active_setting()
        gateway_status = fetch_gateway_status(active_setting)
        gateway_qr_image_data_url = ""
        gateway_qr_message = ""
        if gateway_status.configured and gateway_status.reachable and not gateway_status.connected:
            qr_response = fetch_gateway_qr(active_setting)
            if qr_response.ok:
                gateway_qr_image_data_url = qr_response.data.get("qrImageDataUrl", "") or ""
                gateway_qr_message = qr_response.data.get("message", "") or ""
            else:
                gateway_qr_message = qr_response.summary

        return JsonResponse(
            {
                "configured": gateway_status.configured,
                "reachable": gateway_status.reachable,
                "connected": gateway_status.connected,
                "state": gateway_status.state,
                "number": gateway_status.number,
                "last_error": gateway_status.last_error,
                "qr_image_data_url": gateway_qr_image_data_url,
                "qr_message": gateway_qr_message,
            }
        )


class WhatsAppTemplateListView(PanelListView):
    model = WhatsAppMessageTemplate
    page_title = "WhatsApp Templates"
    page_subtitle = "Message templates with placeholders"
    create_url_name = "panel_whatsapp_template_create"
    update_url_name = "panel_whatsapp_template_update"
    columns = [
        {"label": "Template Key", "value": "template_key"},
        {"label": "Title", "value": "title"},
        {"label": "Active", "value": "is_active"},
        {"label": "Updated", "value": "updated_at"},
    ]
    search_fields = ["template_key", "title", "content"]


class WhatsAppTemplateCreateView(PanelCreateView):
    model = WhatsAppMessageTemplate
    form_class = WhatsAppMessageTemplateForm
    page_title = "Create WhatsApp Template"
    back_url_name = "panel_whatsapp_template_list"
    success_message = "WhatsApp template created successfully."
    success_url = reverse_lazy("panel_whatsapp_template_list")


class WhatsAppTemplateUpdateView(PanelUpdateView):
    model = WhatsAppMessageTemplate
    form_class = WhatsAppMessageTemplateForm
    page_title = "Update WhatsApp Template"
    back_url_name = "panel_whatsapp_template_list"
    success_message = "WhatsApp template updated successfully."
    success_url = reverse_lazy("panel_whatsapp_template_list")


class WhatsAppGatewayRestartView(PanelLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        result = restart_gateway_session()
        if result.ok:
            messages.success(request, result.summary)
        else:
            messages.error(request, result.summary)
        return redirect("panel_whatsapp_scan")


class WhatsAppGatewayLogoutView(PanelLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        result = logout_gateway_session()
        if result.ok:
            messages.success(request, result.summary)
        else:
            messages.error(request, result.summary)
        return redirect("panel_whatsapp_scan")
