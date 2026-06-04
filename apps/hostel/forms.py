from django import forms

from config.forms import StyledFormMixin

from .models import Area, Building, Cot, ExcelUploadLog, Floor, Room, Section, SystemSetting


ROOM_TYPE_CHOICES = [
    ("", "Select Room Type"),
    ("ac", "AC"),
    ("non-ac", "Non-AC"),
]


class BaseHostelModelForm(StyledFormMixin, forms.ModelForm):
    def _selected_int(self, raw_value):
        return int(raw_value) if raw_value and str(raw_value).isdigit() else None

    def _bind_dependent_selectors(self, *, area_field=None, building_field=None, section_field=None, floor_field=None):
        selected_area = self._selected_int(self.data.get(area_field)) if area_field else None
        selected_building = self._selected_int(self.data.get(building_field)) if building_field else None
        selected_section = self._selected_int(self.data.get(section_field)) if section_field else None
        selected_floor = self._selected_int(self.data.get(floor_field)) if floor_field else None

        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            if hasattr(instance, "room") and instance.room_id:
                selected_floor = selected_floor or instance.room.floor_id
                selected_section = selected_section or instance.room.floor.section_id
                selected_building = selected_building or instance.room.floor.section.building_id
                selected_area = selected_area or instance.room.floor.section.building.area_id
            elif hasattr(instance, "floor") and instance.floor_id:
                selected_floor = selected_floor or instance.floor_id
                selected_section = selected_section or instance.floor.section_id
                selected_building = selected_building or instance.floor.section.building_id
                selected_area = selected_area or instance.floor.section.building.area_id
            elif hasattr(instance, "section") and instance.section_id:
                selected_section = selected_section or instance.section_id
                selected_building = selected_building or instance.section.building_id
                selected_area = selected_area or instance.section.building.area_id
            elif hasattr(instance, "building") and instance.building_id:
                selected_building = selected_building or instance.building_id
                selected_area = selected_area or instance.building.area_id

        return selected_area, selected_building, selected_section, selected_floor


class AreaForm(BaseHostelModelForm):
    class Meta:
        model = Area
        fields = ["area_name", "description", "status"]


class BuildingForm(BaseHostelModelForm):
    class Meta:
        model = Building
        fields = ["area", "building_name", "description", "status"]
        labels = {
            "building_name": "Society Name",
        }


class SectionForm(BaseHostelModelForm):
    class Meta:
        model = Section
        fields = ["building", "section_name", "description", "status"]
        labels = {
            "building": "Society",
            "section_name": "Building / Wing Name",
        }


class FloorForm(BaseHostelModelForm):
    area = forms.ModelChoiceField(queryset=Area.objects.none(), label="Area", empty_label="Select Area")
    building = forms.ModelChoiceField(queryset=Building.objects.none(), label="Society", empty_label="Select Society")

    class Meta:
        model = Floor
        fields = ["section", "floor_name", "description", "status"]
        labels = {
            "section": "Building / Wing",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_area, selected_building, _, _ = self._bind_dependent_selectors(
            area_field="area",
            building_field="building",
        )

        self.fields["area"].queryset = Area.objects.filter(status="active").order_by("area_name")
        self.fields["building"].queryset = Building.objects.filter(status="active").order_by("building_name")
        self.fields["section"].queryset = Section.objects.filter(status="active").order_by("section_name")

        if selected_area:
            self.fields["building"].queryset = self.fields["building"].queryset.filter(area_id=selected_area)
            self.fields["area"].initial = selected_area
        else:
            self.fields["building"].queryset = self.fields["building"].queryset.none()

        if selected_building:
            self.fields["section"].queryset = self.fields["section"].queryset.filter(building_id=selected_building)
            self.fields["building"].initial = selected_building
        else:
            self.fields["section"].queryset = self.fields["section"].queryset.none()

        self.field_order = ["area", "building", "section", "floor_name", "description", "status"]


class RoomForm(BaseHostelModelForm):
    area = forms.ModelChoiceField(queryset=Area.objects.none(), label="Area", empty_label="Select Area")
    building = forms.ModelChoiceField(queryset=Building.objects.none(), label="Society", empty_label="Select Society")
    section = forms.ModelChoiceField(queryset=Section.objects.none(), label="Building / Wing", empty_label="Select Building / Wing")
    room_type = forms.ChoiceField(choices=ROOM_TYPE_CHOICES, required=False, label="Room Type")

    class Meta:
        model = Room
        fields = ["floor", "room_number", "room_name", "room_type", "description", "status"]
        labels = {
            "floor": "Floor",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_area, selected_building, selected_section, _ = self._bind_dependent_selectors(
            area_field="area",
            building_field="building",
            section_field="section",
        )

        self.fields["area"].queryset = Area.objects.filter(status="active").order_by("area_name")
        self.fields["building"].queryset = Building.objects.filter(status="active").order_by("building_name")
        self.fields["section"].queryset = Section.objects.filter(status="active").order_by("section_name")
        self.fields["floor"].queryset = Floor.objects.filter(status="active").order_by("floor_name")

        if self.instance.pk and self.instance.room_type and not self.is_bound:
            self.fields["room_type"].initial = self.instance.room_type

        if selected_area:
            self.fields["building"].queryset = self.fields["building"].queryset.filter(area_id=selected_area)
            self.fields["area"].initial = selected_area
        else:
            self.fields["building"].queryset = self.fields["building"].queryset.none()

        if selected_building:
            self.fields["section"].queryset = self.fields["section"].queryset.filter(building_id=selected_building)
            self.fields["building"].initial = selected_building
        else:
            self.fields["section"].queryset = self.fields["section"].queryset.none()

        if selected_section:
            self.fields["floor"].queryset = self.fields["floor"].queryset.filter(section_id=selected_section)
            self.fields["section"].initial = selected_section
        else:
            self.fields["floor"].queryset = self.fields["floor"].queryset.none()

        self.field_order = ["area", "building", "section", "floor", "room_number", "room_name", "room_type", "description", "status"]

    def clean_room_type(self):
        return (self.cleaned_data.get("room_type") or "").strip().lower()


class CotForm(BaseHostelModelForm):
    area = forms.ModelChoiceField(queryset=Area.objects.none(), label="Area", empty_label="Select Area")
    building = forms.ModelChoiceField(queryset=Building.objects.none(), label="Society", empty_label="Select Society")
    section = forms.ModelChoiceField(queryset=Section.objects.none(), label="Building / Wing", empty_label="Select Building / Wing")
    floor = forms.ModelChoiceField(queryset=Floor.objects.none(), label="Floor", empty_label="Select Floor")

    class Meta:
        model = Cot
        fields = ["room", "cot_number", "cot_price", "security_deposit", "status", "remarks"]
        labels = {
            "room": "Room",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_area, selected_building, selected_section, selected_floor = self._bind_dependent_selectors(
            area_field="area",
            building_field="building",
            section_field="section",
            floor_field="floor",
        )

        self.fields["area"].queryset = Area.objects.filter(status="active").order_by("area_name")
        self.fields["building"].queryset = Building.objects.filter(status="active").order_by("building_name")
        self.fields["section"].queryset = Section.objects.filter(status="active").order_by("section_name")
        self.fields["floor"].queryset = Floor.objects.filter(status="active").order_by("floor_name")
        self.fields["room"].queryset = Room.objects.filter(status="active").order_by("room_number")

        if selected_area:
            self.fields["building"].queryset = self.fields["building"].queryset.filter(area_id=selected_area)
            self.fields["area"].initial = selected_area
        else:
            self.fields["building"].queryset = self.fields["building"].queryset.none()

        if selected_building:
            self.fields["section"].queryset = self.fields["section"].queryset.filter(building_id=selected_building)
            self.fields["building"].initial = selected_building
        else:
            self.fields["section"].queryset = self.fields["section"].queryset.none()

        if selected_section:
            self.fields["floor"].queryset = self.fields["floor"].queryset.filter(section_id=selected_section)
            self.fields["section"].initial = selected_section
        else:
            self.fields["floor"].queryset = self.fields["floor"].queryset.none()

        if selected_floor:
            self.fields["room"].queryset = self.fields["room"].queryset.filter(floor_id=selected_floor)
            self.fields["floor"].initial = selected_floor
        else:
            self.fields["room"].queryset = self.fields["room"].queryset.none()

        self.field_order = ["area", "building", "section", "floor", "room", "cot_number", "cot_price", "security_deposit", "status", "remarks"]


class ExcelUploadForm(BaseHostelModelForm):
    class Meta:
        model = ExcelUploadLog
        fields = ["uploaded_file"]


class SystemSettingForm(BaseHostelModelForm):
    class Meta:
        model = SystemSetting
        fields = [
            "site_title",
            "admin_contact_label",
            "admin_contact_number",
            "billing_calculation_method",
            "payment_window_start_day",
            "payment_window_end_day",
            "grace_period_days",
        ]
