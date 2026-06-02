from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView

from .forms import WhatsAppMessageTemplateForm, WhatsAppSettingForm
from .models import WhatsAppLog, WhatsAppMessageTemplate, WhatsAppSetting
from .services import (
    ensure_default_templates,
    fetch_gateway_qr,
    fetch_gateway_status,
    get_active_setting,
    logout_gateway_session,
    restart_gateway_session,
)


class WhatsAppDashboardView(PanelLoginRequiredMixin, TemplateView):
    template_name = "admin_panel/whatsapp/dashboard.html"

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
                "page_subtitle": "QR connect, session status, templates, and delivery logs",
                "settings_list": WhatsAppSetting.objects.order_by("-is_active", "-created_at"),
                "templates_list": WhatsAppMessageTemplate.objects.order_by("template_key"),
                "recent_logs": WhatsAppLog.objects.select_related("student").order_by("-created_at")[:20],
                "active_setting": active_setting,
                "gateway_status": gateway_status,
                "gateway_qr_image_data_url": gateway_qr_image_data_url,
                "gateway_qr_message": gateway_qr_message,
            }
        )
        return context


class WhatsAppSettingCreateView(PanelCreateView):
    model = WhatsAppSetting
    form_class = WhatsAppSettingForm
    page_title = "Create WhatsApp Scan Setting"
    back_url_name = "panel_whatsapp_settings"
    success_message = "WhatsApp scan setting created successfully."
    success_url = reverse_lazy("panel_whatsapp_settings")


class WhatsAppSettingUpdateView(PanelUpdateView):
    model = WhatsAppSetting
    form_class = WhatsAppSettingForm
    page_title = "Update WhatsApp Scan Setting"
    back_url_name = "panel_whatsapp_settings"
    success_message = "WhatsApp scan setting updated successfully."
    success_url = reverse_lazy("panel_whatsapp_settings")


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
        return redirect("panel_whatsapp_settings")


class WhatsAppGatewayLogoutView(PanelLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        result = logout_gateway_session()
        if result.ok:
            messages.success(request, result.summary)
        else:
            messages.error(request, result.summary)
        return redirect("panel_whatsapp_settings")
