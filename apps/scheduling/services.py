from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.utils import timezone
from ics import Calendar, Event

from .models import (
    AvailabilityException,
    AvailabilityRule,
    Booking,
    Resource,
    daterange,
    slot_starts_local,
    to_utc,
)

User = get_user_model()


@dataclass(frozen=True)
class Slot:
    starts_local: datetime
    starts_utc: datetime


def get_tz() -> ZoneInfo:
    return ZoneInfo(getattr(settings, "TIME_ZONE", "Europe/Berlin"))


def list_available_slots(resource: Resource, days_ahead: int = 14) -> list[Slot]:
    tz = get_tz()
    today_local = timezone.localdate()
    rules = (
        AvailabilityRule.objects.filter(resource=resource, is_active=True)
        .only("weekday", "start_time_local", "end_time_local", "resource_id")
        .order_by("weekday", "start_time_local")
    )
    rules_by_weekday: dict[int, list[AvailabilityRule]] = {}
    for rule in rules:
        rules_by_weekday.setdefault(rule.weekday, []).append(rule)

    exceptions = {
        ex.date_local: ex
        for ex in AvailabilityException.objects.filter(resource=resource).only(
            "date_local",
            "is_closed",
            "start_time_local",
            "end_time_local",
            "resource_id",
        )
    }

    window_days = daterange(today_local, days_ahead)
    out: list[Slot] = []
    for day_local in window_days:
        exception = exceptions.get(day_local)
        if exception is not None and exception.is_closed:
            continue

        weekday = day_local.weekday()
        day_rules = rules_by_weekday.get(weekday, [])
        if not day_rules:
            continue

        for rule in day_rules:
            start_t = rule.start_time_local
            end_t = rule.end_time_local

            if exception is not None and not exception.is_closed:
                if exception.start_time_local and exception.end_time_local:
                    start_t = exception.start_time_local
                    end_t = exception.end_time_local

            for starts_local_naive in slot_starts_local(day_local, start_t, end_t):
                starts_local = starts_local_naive.replace(tzinfo=tz)
                if starts_local < timezone.now().astimezone(tz):
                    continue
                out.append(Slot(starts_local=starts_local, starts_utc=to_utc(starts_local)))

    booked = set(
        Booking.objects.filter(
            resource=resource,
            starts_at_utc__gte=timezone.now() - timedelta(days=1),
        ).values_list("starts_at_utc", flat=True)
    )
    return [s for s in out if s.starts_utc not in booked]


def user_daily_booking_count(user: User, day_local: date) -> int:
    tz = get_tz()
    start_local = datetime.combine(day_local, datetime.min.time()).replace(tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_utc = to_utc(start_local)
    end_utc = to_utc(end_local)
    return Booking.objects.filter(
        user=user,
        starts_at_utc__gte=start_utc,
        starts_at_utc__lt=end_utc,
    ).count()


def _lock_key(resource_id: int, starts_at_utc: datetime) -> str:
    return f"booking_lock:{resource_id}:{int(starts_at_utc.timestamp())}"


def create_booking(
    *,
    user: User,
    resource: Resource,
    starts_at_utc: datetime,
    request_host: str | None,
) -> Booking:
    tz = get_tz()
    starts_local = timezone.localtime(starts_at_utc, tz)
    day_local = starts_local.date()

    if user_daily_booking_count(user, day_local) >= 5:
        raise ValueError("Daily booking limit reached (max 5/day).")

    key = _lock_key(resource.id, starts_at_utc)
    with cache.lock(key, timeout=10, blocking_timeout=5):
        try:
            with transaction.atomic():
                booking = Booking.objects.create(
                    user=user,
                    resource=resource,
                    starts_at_utc=starts_at_utc,
                )
        except IntegrityError as exc:
            raise ValueError("This slot is already booked.") from exc

    send_booking_email(booking=booking, request_host=request_host)
    return booking


def cancel_booking(*, booking: Booking, acting_user: User) -> None:
    if booking.user_id != acting_user.id and booking.resource.owner_id != acting_user.id:
        raise PermissionError("Not allowed.")
    booking.delete()


def build_ics_bytes(booking: Booking, request_host: str | None) -> bytes:
    tz = get_tz()
    cal = Calendar()
    event = Event()
    event.name = f"Appointment: {booking.resource.name}"
    event.begin = booking.starts_at_utc
    event.end = booking.ends_at_utc
    event.description = f"Resource: {booking.resource.name}"
    if request_host:
        event.url = f"https://{request_host}/booking/"
    event.categories = ["Scheduler Platform"]
    event.created = timezone.now()
    event.last_modified = timezone.now()
    event.uid = f"{booking.id}@scheduler-platform"
    event.transparent = False
    event.begin = booking.starts_at_utc
    event.end = booking.ends_at_utc
    event.alarms = []
    cal.events.add(event)
    return str(cal).encode("utf-8")


def send_booking_email(*, booking: Booking, request_host: str | None) -> None:
    subject = "Your appointment is confirmed"
    starts_local = booking.starts_at_local()
    ends_local = booking.ends_at_local()
    body = (
        "Your appointment is confirmed.\n\n"
        f"Resource: {booking.resource.name}\n"
        f"Starts (local): {starts_local:%Y-%m-%d %H:%M}\n"
        f"Ends (local): {ends_local:%Y-%m-%d %H:%M}\n"
        "\n"
        "ICS file is attached for Google Calendar import."
    )
    msg = EmailMessage(
        subject=subject,
        body=body,
        to=[booking.user.email],
    )
    ics_bytes = build_ics_bytes(booking, request_host)
    msg.attach(filename="appointment.ics", content=ics_bytes, mimetype="text/calendar")
    msg.send(fail_silently=True)