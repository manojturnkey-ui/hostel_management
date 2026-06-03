from django import forms

from config.forms import StyledFormMixin

from .models import Area, Building, Cot, ExcelUploadLog, Floor, Room, Section, SystemSetting


class BaseHostelModelForm(StyledFormMixin, forms.ModelForm):
    pass


class AreaForm(BaseHostelModelForm):
    class Meta:
        model = Area
        fields = ["area_name", "description", "status"]


class BuildingForm(BaseHostelModelForm):
    class Meta:
        model = Building
        fields = ["area", "building_name", "description", "status"]


class SectionForm(BaseHostelModelForm):
    class Meta:
        model = Section
        fields = ["building", "section_name", "description", "status"]


class FloorForm(BaseHostelModelForm):
    class Meta:
        model = Floor
        fields = ["section", "floor_name", "description", "status"]


class RoomForm(BaseHostelModelForm):
    class Meta:
        model = Room
        fields = ["floor", "room_number", "room_name", "room_type", "description", "status"]


class CotForm(BaseHostelModelForm):
    class Meta:
        model = Cot
        fields = ["room", "cot_number", "cot_price", "security_deposit", "status", "remarks"]


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
