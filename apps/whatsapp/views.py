from django.urls import reverse_lazy
from django.views.generic import TemplateView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView

from .forms import WhatsAppMessageTemplateForm, WhatsAppSettingForm
from .models import WhatsAppLog, WhatsAppMessageTemplate, WhatsAppSetting
from .services import ensure_default_templates


class WhatsAppDashboardView(PanelLoginRequiredMixin, TemplateView):
    template_name = "admin_panel/whatsapp/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        ensure_default_templates()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "WhatsApp Settings",
                "page_subtitle": "Provider configuration, templates, and delivery logs",
                "settings_list": WhatsAppSetting.objects.order_by("-is_active", "-created_at"),
                "templates_list": WhatsAppMessageTemplate.objects.order_by("template_key"),
                "recent_logs": WhatsAppLog.objects.select_related("student").order_by("-created_at")[:20],
            }
        )
        return context


class WhatsAppSettingCreateView(PanelCreateView):
    model = WhatsAppSetting
    form_class = WhatsAppSettingForm
    page_title = "Create WhatsApp Setting"
    back_url_name = "panel_whatsapp_settings"
    success_message = "WhatsApp setting created successfully."
    success_url = reverse_lazy("panel_whatsapp_settings")


class WhatsAppSettingUpdateView(PanelUpdateView):
    model = WhatsAppSetting
    form_class = WhatsAppSettingForm
    page_title = "Update WhatsApp Setting"
    back_url_name = "panel_whatsapp_settings"
    success_message = "WhatsApp setting updated successfully."
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
