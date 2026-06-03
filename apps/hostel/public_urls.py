from django.urls import path

from .views import (
    AreaHomeView,
    BlogPublicView,
    BuildingPublicView,
    ContactPublicView,
    CotPublicView,
    FeaturePublicView,
    FloorPublicView,
    RoomPublicView,
    SectionPublicView,
)


urlpatterns = [
    path("", AreaHomeView.as_view(), name="public_home"),
    path("features/", FeaturePublicView.as_view(), name="public_features"),
    path("blogs/", BlogPublicView.as_view(), name="public_blogs"),
    path("contact/", ContactPublicView.as_view(), name="public_contact"),
    path("areas/<int:area_id>/", BuildingPublicView.as_view(), name="public_area_buildings"),
    path("buildings/<int:building_id>/", SectionPublicView.as_view(), name="public_building_sections"),
    path("sections/<int:section_id>/", FloorPublicView.as_view(), name="public_section_floors"),
    path("floors/<int:floor_id>/", RoomPublicView.as_view(), name="public_floor_rooms"),
    path("rooms/<int:room_id>/", CotPublicView.as_view(), name="public_room_cots"),
]
