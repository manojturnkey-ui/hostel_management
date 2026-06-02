from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from config.mixins import PanelLoginRequiredMixin
from config.panel_views import PanelCreateView, PanelListView, PanelUpdateView
from apps.bookings.models import BookingStatusChoices

from .forms import AreaForm, BuildingForm, CotForm, ExcelUploadForm, FloorForm, RoomForm, SectionForm, SystemSettingForm
from .models import (
    ActiveStatusChoices,
    Area,
    Building,
    Cot,
    CotStatusChoices,
    ExcelUploadLog,
    Floor,
    Room,
    Section,
    SystemSetting,
)
from .services import process_excel_upload


class AreaListView(PanelListView):
    model = Area
    page_title = "Areas"
    page_subtitle = "Manage hostel areas dynamically"
    columns = [
        {"label": "Area Name", "value": "area_name"},
        {"label": "Description", "value": "description"},
        {"label": "Status", "value": "status"},
        {"label": "Created", "value": "created_at"},
    ]
    search_fields = ["area_name", "description"]
    create_url_name = "panel_area_create"
    update_url_name = "panel_area_update"


class AreaCreateView(PanelCreateView):
    model = Area
    form_class = AreaForm
    page_title = "Create Area"
    back_url_name = "panel_area_list"
    success_message = "Area created successfully."
    success_url = reverse_lazy("panel_area_list")


class AreaUpdateView(PanelUpdateView):
    model = Area
    form_class = AreaForm
    page_title = "Update Area"
    back_url_name = "panel_area_list"
    success_message = "Area updated successfully."
    success_url = reverse_lazy("panel_area_list")


class BuildingListView(PanelListView):
    model = Building
    page_title = "Buildings"
    page_subtitle = "Manage buildings area-wise"
    columns = [
        {"label": "Area", "value": "area.area_name"},
        {"label": "Building Name", "value": "building_name"},
        {"label": "Description", "value": "description"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["building_name", "area__area_name"]
    create_url_name = "panel_building_create"
    update_url_name = "panel_building_update"


class BuildingCreateView(PanelCreateView):
    model = Building
    form_class = BuildingForm
    page_title = "Create Building"
    back_url_name = "panel_building_list"
    success_message = "Building created successfully."
    success_url = reverse_lazy("panel_building_list")


class BuildingUpdateView(PanelUpdateView):
    model = Building
    form_class = BuildingForm
    page_title = "Update Building"
    back_url_name = "panel_building_list"
    success_message = "Building updated successfully."
    success_url = reverse_lazy("panel_building_list")


class SectionListView(PanelListView):
    model = Section
    page_title = "Sections / Wings"
    page_subtitle = "Manage sections inside each building"
    columns = [
        {"label": "Area", "value": "building.area.area_name"},
        {"label": "Building", "value": "building.building_name"},
        {"label": "Section", "value": "section_name"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["section_name", "building__building_name", "building__area__area_name"]
    create_url_name = "panel_section_create"
    update_url_name = "panel_section_update"


class SectionCreateView(PanelCreateView):
    model = Section
    form_class = SectionForm
    page_title = "Create Section / Wing"
    back_url_name = "panel_section_list"
    success_message = "Section created successfully."
    success_url = reverse_lazy("panel_section_list")


class SectionUpdateView(PanelUpdateView):
    model = Section
    form_class = SectionForm
    page_title = "Update Section / Wing"
    back_url_name = "panel_section_list"
    success_message = "Section updated successfully."
    success_url = reverse_lazy("panel_section_list")


class FloorListView(PanelListView):
    model = Floor
    page_title = "Floors"
    page_subtitle = "Manage floors section-wise"
    columns = [
        {"label": "Building", "value": "section.building.building_name"},
        {"label": "Section", "value": "section.section_name"},
        {"label": "Floor", "value": "floor_name"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["floor_name", "section__section_name", "section__building__building_name"]
    create_url_name = "panel_floor_create"
    update_url_name = "panel_floor_update"


class FloorCreateView(PanelCreateView):
    model = Floor
    form_class = FloorForm
    page_title = "Create Floor"
    back_url_name = "panel_floor_list"
    success_message = "Floor created successfully."
    success_url = reverse_lazy("panel_floor_list")


class FloorUpdateView(PanelUpdateView):
    model = Floor
    form_class = FloorForm
    page_title = "Update Floor"
    back_url_name = "panel_floor_list"
    success_message = "Floor updated successfully."
    success_url = reverse_lazy("panel_floor_list")


class RoomListView(PanelListView):
    model = Room
    page_title = "Rooms"
    page_subtitle = "Manage floor-wise room inventory"
    columns = [
        {"label": "Building", "value": "floor.section.building.building_name"},
        {"label": "Floor", "value": "floor.floor_name"},
        {"label": "Room No.", "value": "room_number"},
        {"label": "Room Name", "value": "room_name"},
        {"label": "Room Type", "value": "room_type"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["room_number", "room_name", "room_type", "floor__floor_name"]
    create_url_name = "panel_room_create"
    update_url_name = "panel_room_update"


class RoomCreateView(PanelCreateView):
    model = Room
    form_class = RoomForm
    page_title = "Create Room"
    back_url_name = "panel_room_list"
    success_message = "Room created successfully."
    success_url = reverse_lazy("panel_room_list")


class RoomUpdateView(PanelUpdateView):
    model = Room
    form_class = RoomForm
    page_title = "Update Room"
    back_url_name = "panel_room_list"
    success_message = "Room updated successfully."
    success_url = reverse_lazy("panel_room_list")


class CotListView(PanelListView):
    model = Cot
    page_title = "Cots"
    page_subtitle = "Manage room-wise cot pricing and status"
    columns = [
        {"label": "Area", "value": "room.floor.section.building.area.area_name"},
        {"label": "Room", "value": "room.room_number"},
        {"label": "Cot No.", "value": "cot_number"},
        {"label": "Price", "value": "cot_price"},
        {"label": "Deposit", "value": "security_deposit"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["cot_number", "room__room_number"]
    create_url_name = "panel_cot_create"
    update_url_name = "panel_cot_update"


class CotCreateView(PanelCreateView):
    model = Cot
    form_class = CotForm
    page_title = "Create Cot"
    back_url_name = "panel_cot_list"
    success_message = "Cot created successfully."
    success_url = reverse_lazy("panel_cot_list")


class CotUpdateView(PanelUpdateView):
    model = Cot
    form_class = CotForm
    page_title = "Update Cot"
    back_url_name = "panel_cot_list"
    success_message = "Cot updated successfully."
    success_url = reverse_lazy("panel_cot_list")


class ExcelUploadView(PanelLoginRequiredMixin, FormView):
    template_name = "admin_panel/hostel/excel_upload.html"
    form_class = ExcelUploadForm
    success_url = reverse_lazy("panel_excel_upload")

    def form_valid(self, form):
        log_entry = form.save(commit=False)
        log_entry.uploaded_by = self.request.user
        log_entry.save()
        process_excel_upload(log_entry)
        if log_entry.failure_count:
            messages.warning(
                self.request,
                f"Upload completed with {log_entry.success_count} success and {log_entry.failure_count} failure rows.",
            )
        else:
            messages.success(self.request, f"Upload completed successfully with {log_entry.success_count} rows.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Excel Bulk Upload",
                "page_subtitle": "Upload hostel hierarchy and cot pricing in bulk",
                "upload_logs": ExcelUploadLog.objects.order_by("-created_at")[:10],
            }
        )
        return context


class SystemSettingView(PanelLoginRequiredMixin, FormView):
    template_name = "admin_panel/settings/system_settings.html"
    form_class = SystemSettingForm
    success_url = reverse_lazy("panel_system_settings")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = SystemSetting.objects.order_by("id").first() or SystemSetting()
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "System settings updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": "Settings", "page_subtitle": "Billing and site configuration"})
        return context


class AreaHomeView(TemplateView):
    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Hostel Management"
        context["areas"] = Area.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("area_name")
        return context


class BuildingPublicView(TemplateView):
    template_name = "public/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        area = get_object_or_404(Area, pk=self.kwargs["area_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": area.area_name,
                "page_description": "Select a building",
                "items": area.buildings.filter(status=ActiveStatusChoices.ACTIVE).order_by("building_name"),
                "item_type": "building",
                "parent": area,
            }
        )
        return context


class SectionPublicView(TemplateView):
    template_name = "public/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        building = get_object_or_404(Building, pk=self.kwargs["building_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": building.building_name,
                "page_description": "Select a section or wing",
                "items": building.sections.filter(status=ActiveStatusChoices.ACTIVE).order_by("section_name"),
                "item_type": "section",
                "parent": building,
            }
        )
        return context


class FloorPublicView(TemplateView):
    template_name = "public/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section = get_object_or_404(Section, pk=self.kwargs["section_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": section.section_name,
                "page_description": "Select a floor",
                "items": section.floors.filter(status=ActiveStatusChoices.ACTIVE).order_by("floor_name"),
                "item_type": "floor",
                "parent": section,
            }
        )
        return context


class RoomPublicView(TemplateView):
    template_name = "public/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        floor = get_object_or_404(Floor, pk=self.kwargs["floor_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": floor.floor_name,
                "page_description": "Select a room",
                "items": floor.rooms.filter(status=ActiveStatusChoices.ACTIVE).order_by("room_number"),
                "item_type": "room",
                "parent": floor,
            }
        )
        return context


class CotPublicView(TemplateView):
    template_name = "public/cots.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = get_object_or_404(Room, pk=self.kwargs["room_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": room.full_label(),
                "page_description": "Select your cot",
                "room": room,
                "cots": room.cots.order_by("cot_number"),
                "confirmed_status": BookingStatusChoices.CONFIRMED,
                "cot_available": CotStatusChoices.AVAILABLE,
            }
        )
        return context
