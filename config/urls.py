from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("apps.hostel.public_urls")),
    path("", include("apps.bookings.public_urls")),
    path("panel/", include("apps.accounts.urls")),
    path("panel/", include("apps.hostel.urls")),
    path("panel/", include("apps.bookings.urls")),
    path("panel/", include("apps.payments.urls")),
    path("panel/", include("apps.whatsapp.urls")),
    path("panel/", include("apps.access_control.urls")),
    path("panel/", include("apps.reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
