from django.urls import path

from .views import ReportResultView, ReportsHomeView


urlpatterns = [
    path("reports/", ReportsHomeView.as_view(), name="panel_reports_home"),
    path("reports/<str:report_key>/", ReportResultView.as_view(), name="panel_report_result"),
]
