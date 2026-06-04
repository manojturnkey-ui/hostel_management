from django.contrib import messages
from django.db.models.deletion import ProtectedError, RestrictedError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
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


def _safe_int(value):
    return int(value) if value and str(value).isdigit() else None


def _build_filter_collections():
    return {
        "areas": Area.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("area_name"),
        "buildings": Building.objects.filter(status=ActiveStatusChoices.ACTIVE).select_related("area").order_by("building_name"),
        "sections": Section.objects.filter(status=ActiveStatusChoices.ACTIVE).select_related("building", "building__area").order_by("section_name"),
        "floors": Floor.objects.filter(status=ActiveStatusChoices.ACTIVE).select_related("section", "section__building").order_by("floor_name"),
        "rooms": Room.objects.filter(status=ActiveStatusChoices.ACTIVE).select_related(
            "floor",
            "floor__section",
            "floor__section__building",
            "floor__section__building__area",
        ).order_by("room_number"),
    }


def _hostel_relation_options():
    return {
        "buildings": [
            {"id": item.pk, "label": item.building_name, "area_id": item.area_id}
            for item in Building.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("building_name")
        ],
        "sections": [
            {"id": item.pk, "label": item.section_name, "building_id": item.building_id}
            for item in Section.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("section_name")
        ],
        "floors": [
            {"id": item.pk, "label": item.floor_name, "section_id": item.section_id}
            for item in Floor.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("floor_name")
        ],
        "rooms": [
            {"id": item.pk, "label": item.full_label(), "floor_id": item.floor_id}
            for item in Room.objects.filter(status=ActiveStatusChoices.ACTIVE).order_by("room_number")
        ],
    }


def _filtered_cots(area_id=None, building_id=None, section_id=None, floor_id=None, room_id=None, room_types=None, cot_capacities=None):
    queryset = Cot.objects.select_related("room__floor__section__building__area").order_by(
        "room__floor__section__building__area__area_name",
        "room__floor__section__building__building_name",
        "room__floor__section__section_name",
        "room__floor__floor_name",
        "room__room_number",
        "cot_number",
    )
    if area_id:
        queryset = queryset.filter(room__floor__section__building__area_id=area_id)
    if building_id:
        queryset = queryset.filter(room__floor__section__building_id=building_id)
    if section_id:
        queryset = queryset.filter(room__floor__section_id=section_id)
    if floor_id:
        queryset = queryset.filter(room__floor_id=floor_id)
    if room_id:
        queryset = queryset.filter(room_id=room_id)
    if room_types:
        room_type_filter = Q()
        for room_type in room_types:
            room_type_filter |= Q(room__room_type__iexact=room_type)
        queryset = queryset.filter(room_type_filter)
    if cot_capacities:
        room_ids = Room.objects.annotate(cot_total=Count("cots")).filter(cot_total__in=cot_capacities).values_list("id", flat=True)
        queryset = queryset.filter(room_id__in=room_ids)
    return queryset


def _group_room_results(cots):
    grouped = []
    current_room_id = None
    current_group = None
    for cot in cots:
        if cot.room_id != current_room_id:
            current_room_id = cot.room_id
            current_group = {"room": cot.room, "cots": []}
            grouped.append(current_group)
        current_group["cots"].append(cot)
    return grouped


def _feature_explorer_state(*, selected_area=None, selected_building=None, selected_section=None, selected_floor=None, selected_room=None):
    if selected_room:
        return {
            "level": "cot",
            "heading": "Available Cots",
            "subtitle": "Choose a cot from the selected room and continue to booking.",
        }
    if selected_floor:
        return {
            "level": "room",
            "heading": "Choose Room",
            "subtitle": "Select a room to see the available cots inside it.",
        }
    if selected_section:
        return {
            "level": "floor",
            "heading": "Choose Floor",
            "subtitle": "Select a floor inside this building or wing.",
        }
    if selected_building:
        return {
            "level": "section",
            "heading": "Choose Building / Wing",
            "subtitle": "Select the building or wing available inside this society.",
        }
    if selected_area:
        return {
            "level": "building",
            "heading": "Choose Society",
            "subtitle": "Select the society available for the chosen area.",
        }
    return {
        "level": "area",
        "heading": "Choose Area",
        "subtitle": "Start from the hostel area and move step by step until cot selection.",
    }


def _dummy_testimonials():
    return [
        {
            "name": "Aman Verma",
            "role": "Guest from Jaipur",
            "message": "The booking flow felt smooth from area selection to QR payment, and the guest login helped me track approval without calling the office.",
            "image": "public/tourex/img/testimonial/tes-4/tes-1.png",
        },
        {
            "name": "Priya Shah",
            "role": "Working Professional",
            "message": "I liked that I could see cot status clearly before paying. The room and cot details were much more transparent than most hostel sites.",
            "image": "public/tourex/img/testimonial/tes-4/tes-2.png",
        },
        {
            "name": "Rohan Kulkarni",
            "role": "University Guest",
            "message": "The portal made it easy to check my request status and latest payment without confusion. The interface feels modern and trustworthy.",
            "image": "public/tourex/img/testimonial/tes-4/tes-3.png",
        },
        {
            "name": "Neha Singh",
            "role": "Returning Guest",
            "message": "The structure from area to cot was simple to follow, and the guest dashboard kept everything important in one place after booking.",
            "image": "public/tourex/img/testimonial/tes-4/tes-4.png",
        },
    ]


def _public_contact_context():
    system_setting = SystemSetting.get_solo()
    return {
        "public_contact_label": system_setting.admin_contact_label or "Need Help?",
        "public_contact_number": system_setting.admin_contact_number or "+91 98765 43210",
    }


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
    delete_url_name = "panel_area_delete"
    bulk_delete_url_name = "panel_area_bulk_delete"


class AreaCreateView(PanelCreateView):
    model = Area
    form_class = AreaForm
    page_title = "Create Area"
    back_url_name = "panel_area_list"
    success_message = "Area created successfully."
    success_url = reverse_lazy("panel_area_list")


class HostelDependentFormContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["relation_options"] = _hostel_relation_options()
        return context


class AreaUpdateView(PanelUpdateView):
    model = Area
    form_class = AreaForm
    page_title = "Update Area"
    back_url_name = "panel_area_list"
    success_message = "Area updated successfully."
    success_url = reverse_lazy("panel_area_list")


class BuildingListView(PanelListView):
    model = Building
    page_title = "Society"
    page_subtitle = "Manage society area-wise"
    columns = [
        {"label": "Area", "value": "area.area_name"},
        {"label": "Society Name", "value": "building_name"},
        {"label": "Description", "value": "description"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["building_name", "area__area_name"]
    create_url_name = "panel_building_create"
    update_url_name = "panel_building_update"
    delete_url_name = "panel_building_delete"
    bulk_delete_url_name = "panel_building_bulk_delete"


class BuildingCreateView(PanelCreateView):
    model = Building
    form_class = BuildingForm
    page_title = "Create Society"
    back_url_name = "panel_building_list"
    success_message = "Society created successfully."
    success_url = reverse_lazy("panel_building_list")


class BuildingUpdateView(PanelUpdateView):
    model = Building
    form_class = BuildingForm
    page_title = "Update Society"
    back_url_name = "panel_building_list"
    success_message = "Society updated successfully."
    success_url = reverse_lazy("panel_building_list")


class SectionListView(PanelListView):
    model = Section
    page_title = "Buildings / Wings"
    page_subtitle = "Manage buildings or wings inside each society"
    columns = [
        {"label": "Area", "value": "building.area.area_name"},
        {"label": "Society", "value": "building.building_name"},
        {"label": "Building / Wing", "value": "section_name"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["section_name", "building__building_name", "building__area__area_name"]
    create_url_name = "panel_section_create"
    update_url_name = "panel_section_update"
    delete_url_name = "panel_section_delete"
    bulk_delete_url_name = "panel_section_bulk_delete"


class SectionCreateView(PanelCreateView):
    model = Section
    form_class = SectionForm
    page_title = "Create Building / Wing"
    back_url_name = "panel_section_list"
    success_message = "Building / Wing created successfully."
    success_url = reverse_lazy("panel_section_list")


class SectionUpdateView(PanelUpdateView):
    model = Section
    form_class = SectionForm
    page_title = "Update Building / Wing"
    back_url_name = "panel_section_list"
    success_message = "Building / Wing updated successfully."
    success_url = reverse_lazy("panel_section_list")


class FloorListView(PanelListView):
    model = Floor
    page_title = "Floors"
    page_subtitle = "Manage floors section-wise"
    columns = [
        {"label": "Society", "value": "section.building.building_name"},
        {"label": "Building / Wing", "value": "section.section_name"},
        {"label": "Floor", "value": "floor_name"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["floor_name", "section__section_name", "section__building__building_name"]
    create_url_name = "panel_floor_create"
    update_url_name = "panel_floor_update"
    delete_url_name = "panel_floor_delete"
    bulk_delete_url_name = "panel_floor_bulk_delete"


class FloorCreateView(HostelDependentFormContextMixin, PanelCreateView):
    model = Floor
    form_class = FloorForm
    page_title = "Create Floor"
    back_url_name = "panel_floor_list"
    success_message = "Floor created successfully."
    success_url = reverse_lazy("panel_floor_list")


class FloorUpdateView(HostelDependentFormContextMixin, PanelUpdateView):
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
        {"label": "Society", "value": "floor.section.building.building_name"},
        {"label": "Floor", "value": "floor.floor_name"},
        {"label": "Room No.", "value": "room_number"},
        {"label": "Room Name", "value": "room_name"},
        {"label": "Room Type", "value": "room_type"},
        {"label": "Status", "value": "status"},
    ]
    search_fields = ["room_number", "room_name", "room_type", "floor__floor_name"]
    create_url_name = "panel_room_create"
    update_url_name = "panel_room_update"
    delete_url_name = "panel_room_delete"
    bulk_delete_url_name = "panel_room_bulk_delete"


class RoomCreateView(HostelDependentFormContextMixin, PanelCreateView):
    model = Room
    form_class = RoomForm
    page_title = "Create Room"
    back_url_name = "panel_room_list"
    success_message = "Room created successfully."
    success_url = reverse_lazy("panel_room_list")


class RoomUpdateView(HostelDependentFormContextMixin, PanelUpdateView):
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
    delete_url_name = "panel_cot_delete"
    bulk_delete_url_name = "panel_cot_bulk_delete"


class CotCreateView(HostelDependentFormContextMixin, PanelCreateView):
    model = Cot
    form_class = CotForm
    page_title = "Create Cot"
    back_url_name = "panel_cot_list"
    success_message = "Cot created successfully."
    success_url = reverse_lazy("panel_cot_list")


class CotUpdateView(HostelDependentFormContextMixin, PanelUpdateView):
    model = Cot
    form_class = CotForm
    page_title = "Update Cot"
    back_url_name = "panel_cot_list"
    success_message = "Cot updated successfully."
    success_url = reverse_lazy("panel_cot_list")


class BaseHostelDeleteView(PanelLoginRequiredMixin, View):
    model = None
    success_url = ""
    object_label = "Record"

    def post(self, request, pk, *args, **kwargs):
        instance = get_object_or_404(self.model, pk=pk)
        try:
            instance.delete()
            messages.success(request, f"{self.object_label} deleted successfully.")
        except (ProtectedError, RestrictedError):
            messages.error(request, f"{self.object_label} cannot be deleted because it is linked to other records.")
        except Exception as exc:
            messages.error(request, f"Unable to delete {self.object_label.lower()}: {exc}")
        return redirect(self.success_url)


class BaseHostelBulkDeleteView(PanelLoginRequiredMixin, View):
    model = None
    success_url = ""
    object_label = "records"

    def post(self, request, *args, **kwargs):
        selected_ids = [
            int(item)
            for item in request.POST.get("selected_ids", "").split(",")
            if str(item).isdigit()
        ]
        if not selected_ids:
            messages.warning(request, "Select at least one record to delete.")
            return redirect(self.success_url)

        deleted_count = 0
        blocked_count = 0
        for instance in self.model.objects.filter(pk__in=selected_ids):
            try:
                instance.delete()
                deleted_count += 1
            except (ProtectedError, RestrictedError):
                blocked_count += 1
            except Exception:
                blocked_count += 1

        if deleted_count:
            messages.success(request, f"Deleted {deleted_count} {self.object_label}.")
        if blocked_count:
            messages.warning(request, f"{blocked_count} {self.object_label} could not be deleted because they are linked to other records.")
        return redirect(self.success_url)


class AreaDeleteView(BaseHostelDeleteView):
    model = Area
    success_url = reverse_lazy("panel_area_list")
    object_label = "Area"


class AreaBulkDeleteView(BaseHostelBulkDeleteView):
    model = Area
    success_url = reverse_lazy("panel_area_list")
    object_label = "areas"


class BuildingDeleteView(BaseHostelDeleteView):
    model = Building
    success_url = reverse_lazy("panel_building_list")
    object_label = "Society"


class BuildingBulkDeleteView(BaseHostelBulkDeleteView):
    model = Building
    success_url = reverse_lazy("panel_building_list")
    object_label = "societies"


class SectionDeleteView(BaseHostelDeleteView):
    model = Section
    success_url = reverse_lazy("panel_section_list")
    object_label = "Building / Wing"


class SectionBulkDeleteView(BaseHostelBulkDeleteView):
    model = Section
    success_url = reverse_lazy("panel_section_list")
    object_label = "buildings / wings"


class FloorDeleteView(BaseHostelDeleteView):
    model = Floor
    success_url = reverse_lazy("panel_floor_list")
    object_label = "Floor"


class FloorBulkDeleteView(BaseHostelBulkDeleteView):
    model = Floor
    success_url = reverse_lazy("panel_floor_list")
    object_label = "floors"


class RoomDeleteView(BaseHostelDeleteView):
    model = Room
    success_url = reverse_lazy("panel_room_list")
    object_label = "Room"


class RoomBulkDeleteView(BaseHostelBulkDeleteView):
    model = Room
    success_url = reverse_lazy("panel_room_list")
    object_label = "rooms"


class CotDeleteView(BaseHostelDeleteView):
    model = Cot
    success_url = reverse_lazy("panel_cot_list")
    object_label = "Cot"


class CotBulkDeleteView(BaseHostelBulkDeleteView):
    model = Cot
    success_url = reverse_lazy("panel_cot_list")
    object_label = "cots"


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
        filters = _build_filter_collections()
        context["page_title"] = "Hostel Management"
        context["areas"] = filters["areas"]
        context["all_areas"] = filters["areas"]
        context["all_buildings"] = filters["buildings"]
        context["all_sections"] = filters["sections"]
        context["all_floors"] = filters["floors"]
        context["all_rooms"] = filters["rooms"]
        context["top_cots"] = Cot.objects.select_related("room__floor__section__building__area").order_by("-cot_price", "cot_number")[:6]
        context["who_we_are_testimonials"] = _dummy_testimonials()[:2]
        context["guest_testimonials"] = _dummy_testimonials()
        return context


class FeaturePublicView(TemplateView):
    template_name = "public/features.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = _build_filter_collections()
        selected_area = _safe_int(self.request.GET.get("area"))
        selected_building = _safe_int(self.request.GET.get("building"))
        selected_section = _safe_int(self.request.GET.get("section"))
        selected_floor = _safe_int(self.request.GET.get("floor"))
        selected_room = _safe_int(self.request.GET.get("room"))
        selected_room_types = [value for value in self.request.GET.getlist("room_type") if value in {"ac", "non-ac"}]
        selected_cot_capacities = sorted({int(value) for value in self.request.GET.getlist("cot_capacity") if str(value).isdigit()})

        filtered_rooms = filters["rooms"]
        if selected_area:
            filtered_rooms = filtered_rooms.filter(floor__section__building__area_id=selected_area)
        if selected_building:
            filtered_rooms = filtered_rooms.filter(floor__section__building_id=selected_building)
        if selected_section:
            filtered_rooms = filtered_rooms.filter(floor__section_id=selected_section)
        if selected_floor:
            filtered_rooms = filtered_rooms.filter(floor_id=selected_floor)
        if selected_room_types:
            room_type_filter = Q()
            for room_type in selected_room_types:
                room_type_filter |= Q(room_type__iexact=room_type)
            filtered_rooms = filtered_rooms.filter(room_type_filter)

        cot_capacity_options = list(
            filtered_rooms.annotate(cot_total=Count("cots"))
            .values_list("cot_total", flat=True)
            .distinct()
            .order_by("cot_total")
        )
        cot_capacity_options = [value for value in cot_capacity_options if value]
        if selected_cot_capacities:
            filtered_rooms = filtered_rooms.annotate(cot_total=Count("cots")).filter(cot_total__in=selected_cot_capacities)

        explorer_state = _feature_explorer_state(
            selected_area=selected_area,
            selected_building=selected_building,
            selected_section=selected_section,
            selected_floor=selected_floor,
            selected_room=selected_room,
        )

        explorer_items = []
        if explorer_state["level"] == "area":
            explorer_items = list(filters["areas"])
        elif explorer_state["level"] == "building":
            explorer_items = list(filters["buildings"].filter(area_id=selected_area))
        elif explorer_state["level"] == "section":
            explorer_items = list(filters["sections"].filter(building_id=selected_building))
        elif explorer_state["level"] == "floor":
            explorer_items = list(filters["floors"].filter(section_id=selected_section))
        elif explorer_state["level"] == "room":
            explorer_items = list(filtered_rooms.filter(floor_id=selected_floor))

        matching_cots = list(
            _filtered_cots(
                selected_area,
                selected_building,
                selected_section,
                selected_floor,
                selected_room,
                selected_room_types,
                selected_cot_capacities,
            )
        )
        context.update(
            {
                "page_title": "Features",
                "page_description": "Explore filtered room and cot availability using the hostel search controls.",
                "all_areas": filters["areas"],
                "all_buildings": filters["buildings"],
                "all_sections": filters["sections"],
                "all_floors": filters["floors"],
                "all_rooms": filters["rooms"],
                "selected_filters": {
                    "area": selected_area,
                    "building": selected_building,
                    "section": selected_section,
                    "floor": selected_floor,
                    "room": selected_room,
                    "room_types": selected_room_types,
                    "cot_capacities": selected_cot_capacities,
                },
                "room_type_options": [
                    {"value": "ac", "label": "AC"},
                    {"value": "non-ac", "label": "Non-AC"},
                ],
                "cot_capacity_options": cot_capacity_options,
                "matching_cots": matching_cots,
                "room_groups": _group_room_results(matching_cots),
                "top_cots": Cot.objects.select_related("room__floor__section__building__area").order_by("-cot_price", "cot_number")[:12],
                "explorer_state": explorer_state,
                "explorer_items": explorer_items,
            }
        )
        return context


class ContactPublicView(TemplateView):
    template_name = "public/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = _public_contact_context()
        context.update(
            {
                "page_title": "Contact Us",
                "page_description": "Reach the hostel team for booking support, payment help, or room allocation queries.",
                "contact_cards": [
                    {
                        "title": "Visit Hostel Desk",
                        "value": "58 Hostel Avenue, Main Campus Road",
                        "copy": "For room visits, cot confirmations, and offline support.",
                    },
                    {
                        "title": "Call Support",
                        "value": contact["public_contact_number"],
                        "copy": "Available for payment verification and booking assistance.",
                    },
                    {
                        "title": "Email Support",
                        "value": "support@gmail.com",
                        "copy": "Send screenshots, billing questions, or onboarding requests.",
                    },
                ],
                "guest_testimonials": _dummy_testimonials()[:3],
            }
        )
        return context


class BuildingPublicView(TemplateView):
    template_name = "public/hierarchy.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        area = get_object_or_404(Area, pk=self.kwargs["area_id"], status=ActiveStatusChoices.ACTIVE)
        context.update(
            {
                "page_title": area.area_name,
                "page_description": "Select a society",
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
                "page_description": "Select a building or wing",
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


class CotPublicView(View):
    def get(self, request, *args, **kwargs):
        room = get_object_or_404(Room, pk=self.kwargs["room_id"], status=ActiveStatusChoices.ACTIVE)
        return redirect(f"{reverse('public_features')}?room={room.pk}")
