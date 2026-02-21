from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings
from django.utils import timezone

from .models import Resource
from .services import get_tz, list_available_slots


class BookingCreateForm(forms.Form):
    resource_id = forms.IntegerField(widget=forms.HiddenInput())
    starts_at_utc = forms.DateTimeField(widget=forms.HiddenInput())

    def __init__(self, *args, user, resource: Resource, **kwargs):
        self.user = user
        self.resource = resource
        super().__init__(*args, **kwargs)

    def clean_resource_id(self) -> int:
        rid = self.cleaned_data["resource_id"]
        if rid != self.resource.id:
            raise forms.ValidationError("Invalid resource.")
        return rid

    def clean_starts_at_utc(self) -> datetime:
        dt = self.cleaned_data["starts_at_utc"]
        if timezone.is_naive(dt):
            dt = dt.replace(tzinfo=timezone.utc)

        if dt < timezone.now():
            raise forms.ValidationError("Slot is in the past.")

        available = {s.starts_utc for s in list_available_slots(self.resource, days_ahead=21)}
        if dt not in available:
            raise forms.ValidationError("Slot is not available.")

        return dt