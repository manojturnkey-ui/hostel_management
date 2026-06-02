from django import forms

from config.forms import StyledFormMixin
from apps.hostel.models import Area, Building, Floor, Room, Section


class ReportFilterForm(StyledFormMixin, forms.Form):
    STATUS_CHOICES = [
        ("", "All Statuses"),
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("available", "Available"),
        ("pending", "Pending"),
        ("occupied", "Occupied"),
        ("maintenance", "Maintenance"),
        ("blocked", "Blocked"),
        ("pending_admin_confirmation", "Pending Booking"),
        ("confirmed", "Confirmed"),
        ("rejected", "Rejected"),
        ("unpaid", "Unpaid"),
        ("pending_verification", "Pending Verification"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("allowed", "Allowed"),
        ("denied", "Denied"),
    ]

    area = forms.ModelChoiceField(queryset=Area.objects.none(), required=False, empty_label="All Areas")
    building = forms.ModelChoiceField(queryset=Building.objects.none(), required=False, empty_label="All Buildings")
    section = forms.ModelChoiceField(queryset=Section.objects.none(), required=False, empty_label="All Sections")
    floor = forms.ModelChoiceField(queryset=Floor.objects.none(), required=False, empty_label="All Floors")
    room = forms.ModelChoiceField(queryset=Room.objects.none(), required=False, empty_label="All Rooms")
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput)
    date_to = forms.DateField(required=False, widget=forms.DateInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.order_by("area_name")
        self.fields["building"].queryset = Building.objects.select_related("area").order_by("building_name")
        self.fields["section"].queryset = Section.objects.select_related("building").order_by("section_name")
        self.fields["floor"].queryset = Floor.objects.select_related("section").order_by("floor_name")
        self.fields["room"].queryset = Room.objects.select_related("floor").order_by("room_number")
