from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import QuerySet

from .models import AvailabilityException, AvailabilityRule, Booking, Resource


def _is_manager(user) -> bool:
    return user.is_authenticated and user.groups.filter(name="manager").exists()


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "owner__email")

    def get_queryset(self, request) -> QuerySet:
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_staff and not _is_manager(request.user):
            return qs
        if _is_manager(request.user):
            return qs.filter(owner=request.user)
        return qs.none()

    def save_model(self, request, obj, form, change) -> None:
        if not change and _is_manager(request.user):
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ("resource", "weekday", "start_time_local", "end_time_local", "is_active")
    list_filter = ("weekday", "is_active")
    search_fields = ("resource__name",)

    def get_queryset(self, request) -> QuerySet:
        qs = super().get_queryset(request).select_related("resource", "resource__owner")
        if request.user.is_superuser or request.user.is_staff and not _is_manager(request.user):
            return qs
        if _is_manager(request.user):
            return qs.filter(resource__owner=request.user)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "resource" and _is_manager(request.user):
            kwargs["queryset"] = Resource.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ("resource", "date_local", "is_closed", "start_time_local", "end_time_local")
    list_filter = ("is_closed", "date_local")
    search_fields = ("resource__name",)

    def get_queryset(self, request) -> QuerySet:
        qs = super().get_queryset(request).select_related("resource", "resource__owner")
        if request.user.is_superuser or request.user.is_staff and not _is_manager(request.user):
            return qs
        if _is_manager(request.user):
            return qs.filter(resource__owner=request.user)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "resource" and _is_manager(request.user):
            kwargs["queryset"] = Resource.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "resource", "user", "starts_at_utc", "created_at_utc")
    search_fields = ("resource__name", "user__email")
    list_filter = ("resource",)

    def get_queryset(self, request) -> QuerySet:
        qs = super().get_queryset(request).select_related("resource", "resource__owner", "user")
        if request.user.is_superuser or request.user.is_staff and not _is_manager(request.user):
            return qs
        if _is_manager(request.user):
            return qs.filter(resource__owner=request.user)
        return qs.none()