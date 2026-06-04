from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .mixins import PanelLoginRequiredMixin


class PanelTemplateView(PanelLoginRequiredMixin, TemplateView):
    page_title = ""
    page_subtitle = ""
    breadcrumbs = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "breadcrumbs": self.breadcrumbs,
            }
        )
        return context


class PanelListView(PanelLoginRequiredMixin, ListView):
    template_name = "admin_panel/shared/list.html"
    context_object_name = "object_list"
    paginate_by = 20
    page_title = ""
    page_subtitle = ""
    breadcrumbs = []
    columns = []
    search_fields = []
    create_url_name = ""
    update_url_name = ""
    detail_url_name = ""
    delete_url_name = ""
    bulk_delete_url_name = ""

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.get_search_query()
        if query and self.search_fields:
            filters = Q()
            for field in self.search_fields:
                filters |= Q(**{f"{field}__icontains": query})
            queryset = queryset.filter(filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "breadcrumbs": self.breadcrumbs,
                "columns": self.columns,
                "search_query": self.get_search_query(),
                "create_url_name": self.create_url_name,
                "update_url_name": self.update_url_name,
                "detail_url_name": self.detail_url_name,
                "delete_url_name": self.delete_url_name,
                "bulk_delete_url_name": self.bulk_delete_url_name,
            }
        )
        return context


class PanelCreateView(PanelLoginRequiredMixin, CreateView):
    template_name = "admin_panel/shared/form.html"
    page_title = ""
    page_subtitle = ""
    breadcrumbs = []
    success_message = "Saved successfully."
    back_url_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "breadcrumbs": self.breadcrumbs,
                "back_url_name": self.back_url_name,
                "submit_label": "Create",
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class PanelUpdateView(PanelLoginRequiredMixin, UpdateView):
    template_name = "admin_panel/shared/form.html"
    page_title = ""
    page_subtitle = ""
    breadcrumbs = []
    success_message = "Updated successfully."
    back_url_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "breadcrumbs": self.breadcrumbs,
                "back_url_name": self.back_url_name,
                "submit_label": "Update",
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response
