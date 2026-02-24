from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Resource(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_resources",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}"


class AvailabilityRule(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="availability_rules",
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["resource_id", "weekday", "start_time_local"]

    def __str__(self) -> str:
        return f"{self.resource_id} {self.weekday} {self.start_time_local}-{self.end_time_local}"


class AvailabilityException(models.Model):
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="availability_exceptions",
    )
    date_local = models.DateField()
    is_closed = models.BooleanField(default=True)
    start_time_local = models.TimeField(blank=True, null=True)
    end_time_local = models.TimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "date_local"],
                name="uniq_exception_per_resource_date",
            )
        ]
        ordering = ["-date_local"]

    def __str__(self) -> str:
        return f"{self.resource_id} {self.date_local}"


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    starts_at_utc = models.DateTimeField()
    created_at_utc = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "starts_at_utc"],
                name="uniq_booking_resource_starts_at_utc",
            )
        ]
        ordering = ["-starts_at_utc"]

    def __str__(self) -> str:
        return f"{self.resource_id} {self.starts_at_utc.isoformat()}"

    @property
    def ends_at_utc(self) -> datetime:
        return self.starts_at_utc + timedelta(minutes=45)

    def starts_at_local(self) -> datetime:
        tz = ZoneInfo(getattr(settings, "TIME_ZONE", "Europe/Berlin"))
        return timezone.localtime(self.starts_at_utc, tz)

    def ends_at_local(self) -> datetime:
        tz = ZoneInfo(getattr(settings, "TIME_ZONE", "Europe/Berlin"))
        return timezone.localtime(self.ends_at_utc, tz)


def daterange(start_date: date, days: int) -> list[date]:
    return [start_date + timedelta(days=idx) for idx in range(days)]


def to_utc(dt_local: datetime) -> datetime:
    return dt_local.astimezone(dt_timezone.utc)


def slot_starts_local(day_local: date, start_t: time, end_t: time) -> list[datetime]:
    start_dt = datetime.combine(day_local, start_t)
    end_dt = datetime.combine(day_local, end_t)
    slot = start_dt
    out: list[datetime] = []
    while slot + timedelta(minutes=45) <= end_dt:
        out.append(slot)
        slot = slot + timedelta(minutes=45)
    return out