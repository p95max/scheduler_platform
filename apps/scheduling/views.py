from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import BookingCreateForm
from .models import Booking, Resource
from .services import cancel_booking, create_booking, list_available_slots


def resource_list(request: HttpRequest) -> HttpResponse:
    resources = (
        Resource.objects.filter(is_active=True)
        .select_related("owner")
        .only("id", "name", "description", "owner_id", "is_active")
        .order_by("name")
    )
    return render(request, "scheduling/resource_list.html", {"resources": resources})


def resource_detail(request: HttpRequest, resource_id: int) -> HttpResponse:
    resource = get_object_or_404(Resource.objects.select_related("owner"), pk=resource_id, is_active=True)
    slots = list_available_slots(resource, days_ahead=14)
    return render(
        request,
        "scheduling/resource_detail.html",
        {"resource": resource, "slots": slots},
    )


@login_required
def booking_create(request: HttpRequest, resource_id: int) -> HttpResponse:
    resource = get_object_or_404(Resource, pk=resource_id, is_active=True)

    if request.method == "POST":
        form = BookingCreateForm(request.POST, user=request.user, resource=resource)
        if form.is_valid():
            try:
                booking = create_booking(
                    user=request.user,
                    resource=resource,
                    starts_at_utc=form.cleaned_data["starts_at_utc"],
                    request_host=request.get_host(),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect(reverse("scheduling:resource_detail", kwargs={"resource_id": resource.id}))
            messages.success(request, "Booked successfully. Check your email for ICS.")
            return redirect(reverse("scheduling:booking_success", kwargs={"booking_id": booking.id}))
        messages.error(request, "Invalid booking data.")
        return redirect(reverse("scheduling:resource_detail", kwargs={"resource_id": resource.id}))

    raise Http404()


@login_required
def booking_success(request: HttpRequest, booking_id) -> HttpResponse:
    booking = get_object_or_404(
        Booking.objects.select_related("resource", "user", "resource__owner"),
        pk=booking_id,
        user=request.user,
    )
    return render(request, "scheduling/booking_success.html", {"booking": booking})


@login_required
def booking_cancel(request: HttpRequest, booking_id) -> HttpResponse:
    booking = get_object_or_404(
        Booking.objects.select_related("resource", "resource__owner"),
        pk=booking_id,
    )
    try:
        cancel_booking(booking=booking, acting_user=request.user)
    except PermissionError:
        raise Http404()
    messages.info(request, "Booking cancelled.")
    return redirect(reverse("scheduling:resource_list"))


@login_required
def my_bookings(request: HttpRequest) -> HttpResponse:
    bookings = (
        Booking.objects.filter(user=request.user)
        .select_related("resource", "resource__owner")
        .only("id", "starts_at_utc", "resource_id", "resource__name", "resource__owner_id")
        .order_by("-starts_at_utc")
    )
    return render(request, "scheduling/my_bookings.html", {"bookings": bookings})


@login_required
def manager_bookings(request: HttpRequest) -> HttpResponse:
    bookings = (
        Booking.objects.filter(resource__owner=request.user)
        .select_related("resource", "user")
        .only("id", "starts_at_utc", "resource_id", "resource__name", "user_id", "user__email")
        .order_by("-starts_at_utc")
    )
    return render(request, "scheduling/manager_bookings.html", {"bookings": bookings})