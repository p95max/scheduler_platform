from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="scheduling:resource_list", permanent=False)),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("booking/", include("apps.scheduling.urls")),
]