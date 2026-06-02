from django.urls import path

from .views import DashboardView, PanelLoginView, PanelLogoutView, PanelRootRedirectView


urlpatterns = [
    path("", PanelRootRedirectView.as_view(), name="panel_root"),
    path("login/", PanelLoginView.as_view(), name="panel_login"),
    path("logout/", PanelLogoutView.as_view(), name="panel_logout"),
    path("dashboard/", DashboardView.as_view(), name="panel_dashboard"),
]
