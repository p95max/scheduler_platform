from django.urls import path

from .views import (
    booking_cancel,
    booking_create,
    booking_success,
    manager_bookings,
    my_bookings,
    resource_detail,
    resource_list,
)

app_name = "scheduling"

urlpatterns = [
    path("", resource_list, name="resource_list"),
    path("resources/<int:resource_id>/", resource_detail, name="resource_detail"),
    path("resources/<int:resource_id>/book/", booking_create, name="booking_create"),
    path("success/<uuid:booking_id>/", booking_success, name="booking_success"),
    path("cancel/<uuid:booking_id>/", booking_cancel, name="booking_cancel"),
    path("me/", my_bookings, name="my_bookings"),
    path("manager/bookings/", manager_bookings, name="manager_bookings"),
]