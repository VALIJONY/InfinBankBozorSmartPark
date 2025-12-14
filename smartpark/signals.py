from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VehicleEntry, Cars
from django.utils import timezone
from datetime import datetime, timedelta


@receiver(post_save, sender=VehicleEntry)
def vehicle_entry_updated(sender, instance, created, **kwargs):
    """Send WebSocket update when VehicleEntry is created or updated"""
    channel_layer = get_channel_layer()

    # Get statistics for today using timezone-aware datetime range
    today = timezone.now().date()
    start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(
        is_paid=False, exit_time__isnull=False
    ).count()

    # Prepare statistics data
    stats_data = {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "total_inside": total_inside,
        "unpaid_entries": unpaid_entries,
    }

    # Get entries that either:
    # 1. Entered today (normal case)
    # 2. Entered yesterday but exited today (overnight parking)
    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )

    # Also include vehicles that entered yesterday but exited today
    yesterday_start = timezone.make_aware(
        datetime.combine(today - timedelta(days=1), datetime.min.time())
    )
    yesterday_end = timezone.make_aware(
        datetime.combine(today - timedelta(days=1), datetime.max.time())
    )

    overnight_entries = VehicleEntry.objects.filter(
        entry_time__gte=yesterday_start,
        entry_time__lte=yesterday_end,
        exit_time__gte=start_datetime,
        exit_time__lte=end_datetime,
    )

    # Get all entry IDs from both querysets
    today_ids = list(today_entries.values_list("id", flat=True))
    overnight_ids = list(overnight_entries.values_list("id", flat=True))
    all_ids = today_ids + overnight_ids

    # Get all entries by IDs and order by entry_time
    entries = VehicleEntry.objects.filter(id__in=all_ids).order_by("-entry_time")
    entries_data = []

    for entry in entries:
        # Calculate duration in hours if exit time exists
        duration_hours = None
        if entry.exit_time and entry.entry_time:
            duration_hours = (entry.exit_time - entry.entry_time).total_seconds() / 3600

        entries_data.append(
            {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry.entry_time.strftime("%H:%M"),
                "exit_time": entry.exit_time.strftime("%H:%M")
                if entry.exit_time
                else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "entry_image": entry.entry_image.url if entry.entry_image else None,
                "exit_image": entry.exit_image.url if entry.exit_image else None,
                "status": "inside"
                if not entry.exit_time
                else ("paid" if entry.is_paid else "unpaid"),
                "duration_hours": duration_hours,
            }
        )

    # Determine action type
    action = "created" if created else "updated"
    if not created and instance.is_paid:
        action = "payment_completed"

    # Broadcast update to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_update",
            "statistics": stats_data,
            "vehicle_entries": entries_data,
            "action": action,
            "entry_id": instance.id,
            "number_plate": instance.number_plate,
        },
    )

    # Send latest unpaid entry update for unpaid entries page
    if instance.exit_time and not instance.is_paid:
        # Get the latest unpaid entry
        latest_unpaid = (
            VehicleEntry.objects.filter(
                entry_time__gte=start_datetime,
                entry_time__lte=end_datetime,
                is_paid=False,
                exit_time__isnull=False,
            )
            .order_by("-exit_time")
            .first()
        )

        if latest_unpaid:
            latest_unpaid_data = {
                "id": latest_unpaid.id,
                "number_plate": latest_unpaid.number_plate,
                "entry_time": latest_unpaid.entry_time.strftime("%H:%M"),
                "exit_time": latest_unpaid.exit_time.strftime("%H:%M"),
                "total_amount": latest_unpaid.total_amount or 0,
                "duration_hours": (
                    latest_unpaid.exit_time - latest_unpaid.entry_time
                ).total_seconds()
                / 3600,
                "entry_image": latest_unpaid.entry_image.url
                if latest_unpaid.entry_image
                else None,
                "exit_image": latest_unpaid.exit_image.url
                if latest_unpaid.exit_image
                else None,
            }
        else:
            latest_unpaid_data = None

        async_to_sync(channel_layer.group_send)(
            "home_updates",
            {
                "type": "latest_unpaid_entry_update",
                "data": latest_unpaid_data,
            },
        )

    # Handle when entry is marked as paid
    if not created and instance.is_paid and instance.exit_time:
        # Get the latest unpaid entry after this one was marked as paid
        latest_unpaid = (
            VehicleEntry.objects.filter(
                entry_time__gte=start_datetime,
                entry_time__lte=end_datetime,
                is_paid=False,
                exit_time__isnull=False,
            )
            .order_by("-exit_time")
            .first()
        )

        if latest_unpaid:
            latest_unpaid_data = {
                "id": latest_unpaid.id,
                "number_plate": latest_unpaid.number_plate,
                "entry_time": latest_unpaid.entry_time.strftime("%H:%M"),
                "exit_time": latest_unpaid.exit_time.strftime("%H:%M"),
                "total_amount": latest_unpaid.total_amount or 0,
                "duration_hours": (
                    latest_unpaid.exit_time - latest_unpaid.entry_time
                ).total_seconds()
                / 3600,
                "entry_image": latest_unpaid.entry_image.url
                if latest_unpaid.entry_image
                else None,
                "exit_image": latest_unpaid.exit_image.url
                if latest_unpaid.exit_image
                else None,
            }
        else:
            latest_unpaid_data = None

        async_to_sync(channel_layer.group_send)(
            "home_updates",
            {
                "type": "latest_unpaid_entry_update",
                "data": latest_unpaid_data,
            },
        )


@receiver(post_delete, sender=VehicleEntry)
def vehicle_entry_deleted(sender, instance, **kwargs):
    """Send WebSocket update when VehicleEntry is deleted"""
    channel_layer = get_channel_layer()

    # Get updated statistics for today using timezone-aware datetime range
    today = timezone.now().date()
    start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(
        is_paid=False, exit_time__isnull=False
    ).count()

    # Prepare statistics data
    stats_data = {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "total_inside": total_inside,
        "unpaid_entries": unpaid_entries,
    }

    # Get entries that either:
    # 1. Entered today (normal case)
    # 2. Entered yesterday but exited today (overnight parking)
    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )

    # Also include vehicles that entered yesterday but exited today
    yesterday_start = timezone.make_aware(
        datetime.combine(today - timedelta(days=1), datetime.min.time())
    )
    yesterday_end = timezone.make_aware(
        datetime.combine(today - timedelta(days=1), datetime.max.time())
    )

    overnight_entries = VehicleEntry.objects.filter(
        entry_time__gte=yesterday_start,
        entry_time__lte=yesterday_end,
        exit_time__gte=start_datetime,
        exit_time__lte=end_datetime,
    )

    # Get all entry IDs from both querysets
    today_ids = list(today_entries.values_list("id", flat=True))
    overnight_ids = list(overnight_entries.values_list("id", flat=True))
    all_ids = today_ids + overnight_ids

    # Get all entries by IDs and order by entry_time
    entries = VehicleEntry.objects.filter(id__in=all_ids).order_by("-entry_time")
    entries_data = []

    for entry in entries:
        # Calculate duration in hours if exit time exists
        duration_hours = None
        if entry.exit_time and entry.entry_time:
            duration_hours = (entry.exit_time - entry.entry_time).total_seconds() / 3600

        entries_data.append(
            {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry.entry_time.strftime("%H:%M"),
                "exit_time": entry.exit_time.strftime("%H:%M")
                if entry.exit_time
                else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "entry_image": entry.entry_image.url if entry.entry_image else None,
                "exit_image": entry.exit_image.url if entry.exit_image else None,
                "status": "inside"
                if not entry.exit_time
                else ("paid" if entry.is_paid else "unpaid"),
                "duration_hours": duration_hours,
            }
        )

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_update",
            "statistics": stats_data,
            "vehicle_entries": entries_data,
            "action": "deleted",
            "entry_id": instance.id,
            "number_plate": instance.number_plate,
        },
    )


@receiver(post_save, sender=Cars)
def car_updated(sender, instance, created, **kwargs):
    """Send WebSocket update when Cars is created or updated"""
    channel_layer = get_channel_layer()

    # Prepare car data
    car_data = {
        "id": instance.id,
        "number_plate": instance.number_plate,
        "is_free": instance.is_free,
        "is_special_taxi": instance.is_special_taxi,
        "is_blocked": instance.is_blocked,
    }

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_car_update",
            "car": car_data,
            "action": "created" if created else "updated",
        },
    )


@receiver(post_delete, sender=Cars)
def car_deleted(sender, instance, **kwargs):
    """Send WebSocket update when Cars is deleted"""
    channel_layer = get_channel_layer()

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_car_update",
            "car": {
                "number_plate": instance.number_plate,
                "is_free": instance.is_free,
                "is_special_taxi": instance.is_special_taxi,
                "is_blocked": instance.is_blocked,
            },
            "action": "deleted",
        },
    )
