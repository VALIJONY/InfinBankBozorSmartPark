import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import datetime
from .models import VehicleEntry


class HomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the home_updates group
        await self.channel_layer.group_add("home_updates", self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to Smart AutoPark WebSocket",
                }
            )
        )

    async def disconnect(self, close_code):
        # Leave the home_updates group
        await self.channel_layer.group_discard("home_updates", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "get_statistics":
            await self.send_statistics(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_vehicle_entries":
            await self.send_vehicle_entries(
                data.get("date", timezone.now().date().isoformat()),
                data.get("search", ""),
            )
        elif message_type == "mark_as_paid":
            await self.handle_mark_as_paid(data.get("entry_id"))
        elif message_type == "delete_entry":
            await self.handle_delete_entry(data.get("entry_id"))
        elif message_type == "get_unpaid_entries":
            await self.send_unpaid_entries(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_latest_unpaid_entry":
            await self.send_latest_unpaid_entry(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_receipt":
            await self.handle_get_receipt(data.get("entry_id"))
        elif message_type == "print_receipt":
            await self.handle_print_receipt(data.get("entry_id"))
        elif message_type == "print_simple_receipt":
            await self.handle_print_simple_receipt(data.get("entry_id"))
        elif message_type == "clear_exit_time":
            await self.handle_clear_exit_time(data.get("entry_id"))
        elif message_type == "find_xprinter":
            await self.handle_find_xprinter()
        elif message_type == "test_xprinter":
            await self.handle_test_xprinter()

    # Handle broadcast messages from signals
    async def broadcast_update(self, event):
        """Handle broadcast updates from VehicleEntry signals"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "model_update",
                    "statistics": event["statistics"],
                    "vehicle_entries": event["vehicle_entries"],
                    "action": event["action"],
                    "entry_id": event.get("entry_id"),
                    "number_plate": event.get("number_plate"),
                }
            )
        )

        # If this is a payment completion, also send latest unpaid entry update
        if event.get("action") == "payment_completed":
            today = timezone.now().date().isoformat()
            latest_unpaid = await self.get_latest_unpaid_entry(today)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "latest_unpaid_entry_update",
                        "data": latest_unpaid,
                    }
                )
            )

    async def broadcast_notification(self, event):
        """Handle broadcast notifications"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "title": event["title"],
                    "message": event["message"],
                    "notification_type": event["notification_type"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def latest_unpaid_entry_update(self, event):
        """Handle latest unpaid entry updates"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "latest_unpaid_entry_update",
                    "data": event["data"],
                }
            )
        )

    @database_sync_to_async
    def get_statistics(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get entries that either:
        # 1. Entered today (normal case)
        # 2. Entered yesterday but exited today (overnight parking)
        today_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime, entry_time__lte=end_datetime
        )

        # Also include vehicles that entered yesterday but exited today
        yesterday_start = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.min.time())
        )
        yesterday_end = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.max.time())
        )

        overnight_entries = VehicleEntry.objects.filter(
            entry_time__gte=yesterday_start,
            entry_time__lte=yesterday_end,
            exit_time__gte=start_datetime,
            exit_time__lte=end_datetime,
        )

        # Calculate statistics separately for each queryset
        today_total = today_entries.count()
        today_exits = today_entries.filter(exit_time__isnull=False).count()
        today_inside = today_entries.filter(exit_time__isnull=True).count()
        today_unpaid = today_entries.filter(
            is_paid=False, exit_time__isnull=False
        ).count()

        overnight_total = overnight_entries.count()
        overnight_exits = overnight_entries.filter(exit_time__isnull=False).count()
        overnight_inside = overnight_entries.filter(exit_time__isnull=True).count()
        overnight_unpaid = overnight_entries.filter(
            is_paid=False, exit_time__isnull=False
        ).count()

        # Combine the results
        total_entries = today_total + overnight_total
        total_exits = today_exits + overnight_exits
        total_inside = today_inside + overnight_inside
        unpaid_entries = today_unpaid + overnight_unpaid

        return {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "total_inside": total_inside,
            "unpaid_entries": unpaid_entries,
        }

    @database_sync_to_async
    def get_vehicle_entries(self, date_str, search_query=""):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get entries that either:
        # 1. Entered today (normal case)
        # 2. Entered yesterday but exited today (overnight parking)
        today_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime, entry_time__lte=end_datetime
        )

        # Also include vehicles that entered yesterday but exited today
        yesterday_start = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.min.time())
        )
        yesterday_end = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.max.time())
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

        # Apply search filter if provided
        if search_query:
            entries = entries.filter(number_plate__icontains=search_query)

        entries_data = []
        for entry in entries:
            # Ensure timezone-aware formatting
            entry_time = entry.entry_time
            exit_time = entry.exit_time

            # Calculate duration in hours across days if exit exists
            duration_hours = (
                (exit_time - entry_time).total_seconds() / 3600 if exit_time else None
            )

            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M") if exit_time else None,
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

        return entries_data

    @database_sync_to_async
    def mark_as_paid(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)
            entry.is_paid = True
            entry.save()

            # Open barrier after successful payment

            # Get updated statistics and vehicle entries for real-time update
            today = timezone.now().date().isoformat()
            stats = self.get_statistics_sync(today)
            vehicle_entries = self.get_vehicle_entries_sync(today, "")
            latest_unpaid = self.get_latest_unpaid_entry_sync(today)

            return {
                "success": True,
                "entry_id": entry_id,
                "statistics": stats,
                "vehicle_entries": vehicle_entries,
                "latest_unpaid_entry": latest_unpaid,
                "auto_print_success": False,
                "auto_print_message": "Chek faqat qo'lda so'ralganda chiqariladi",
                "print_error": "",
            }
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    @database_sync_to_async
    def clear_exit_time(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)

            # Clear exit time and exit image
            entry.exit_time = None
            entry.exit_image = None
            entry.total_amount = None
            entry.is_paid = False
            entry.save()

            # Get updated statistics and vehicle entries for real-time update
            today = timezone.now().date().isoformat()
            stats = self.get_statistics_sync(today)
            vehicle_entries = self.get_vehicle_entries_sync(today, "")
            latest_unpaid = self.get_latest_unpaid_entry_sync(today)

            return {
                "success": True,
                "entry_id": entry_id,
                "number_plate": entry.number_plate,
                "statistics": stats,
                "vehicle_entries": vehicle_entries,
                "latest_unpaid_entry": latest_unpaid,
            }
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    def get_statistics_sync(self, date_str):
        """Synchronous version of get_statistics for use in mark_as_paid"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get entries that either:
        # 1. Entered today (normal case)
        # 2. Entered yesterday but exited today (overnight parking)
        today_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime, entry_time__lte=end_datetime
        )

        # Also include vehicles that entered yesterday but exited today
        yesterday_start = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.min.time())
        )
        yesterday_end = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.max.time())
        )

        overnight_entries = VehicleEntry.objects.filter(
            entry_time__gte=yesterday_start,
            entry_time__lte=yesterday_end,
            exit_time__gte=start_datetime,
            exit_time__lte=end_datetime,
        )

        # Calculate statistics separately for each queryset
        today_total = today_entries.count()
        today_exits = today_entries.filter(exit_time__isnull=False).count()
        today_inside = today_entries.filter(exit_time__isnull=True).count()
        today_unpaid = today_entries.filter(
            is_paid=False, exit_time__isnull=False
        ).count()

        overnight_total = overnight_entries.count()
        overnight_exits = overnight_entries.filter(exit_time__isnull=False).count()
        overnight_inside = overnight_entries.filter(exit_time__isnull=True).count()
        overnight_unpaid = overnight_entries.filter(
            is_paid=False, exit_time__isnull=False
        ).count()

        # Combine the results
        total_entries = today_total + overnight_total
        total_exits = today_exits + overnight_exits
        total_inside = today_inside + overnight_inside
        unpaid_entries = today_unpaid + overnight_unpaid

        return {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "total_inside": total_inside,
            "unpaid_entries": unpaid_entries,
        }

    def get_vehicle_entries_sync(self, date_str, search_query=""):
        """Synchronous version of get_vehicle_entries for use in mark_as_paid"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get entries that either:
        # 1. Entered today (normal case)
        # 2. Entered yesterday but exited today (overnight parking)
        today_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime, entry_time__lte=end_datetime
        )

        # Also include vehicles that entered yesterday but exited today
        yesterday_start = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.min.time())
        )
        yesterday_end = timezone.make_aware(
            datetime.combine(date_obj - timezone.timedelta(days=1), datetime.max.time())
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

        # Apply search filter if provided
        if search_query:
            entries = entries.filter(number_plate__icontains=search_query)

        entries_data = []
        for entry in entries:
            entry_time = entry.entry_time
            exit_time = entry.exit_time

            # Calculate duration in hours across days if exit exists
            duration_hours = (
                (exit_time - entry_time).total_seconds() / 3600 if exit_time else None
            )

            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M") if exit_time else None,
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

        return entries_data

    def get_latest_unpaid_entry_sync(self, date_str):
        """Synchronous version of get_latest_unpaid_entry for use in mark_as_paid"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get the latest unpaid entry that has exited today
        # This includes vehicles that entered yesterday but exited today
        latest_entry = (
            VehicleEntry.objects.filter(
                exit_time__gte=start_datetime,
                exit_time__lte=end_datetime,
                is_paid=False,
                is_error=False,  # Xatolik belgilanganlarni chiqarib tashlash
                exit_time__isnull=False,
            )
            .order_by("-exit_time")
            .first()
        )

        if latest_entry:
            entry_time = latest_entry.entry_time
            exit_time = latest_entry.exit_time

            return {
                "id": latest_entry.id,
                "number_plate": latest_entry.number_plate,
                "entry_time": entry_time.strftime("%H:%M"),
                "exit_time": exit_time.strftime("%H:%M"),
                "total_amount": latest_entry.total_amount or 0,
                "duration_hours": (exit_time - entry_time).total_seconds() / 3600,
                "entry_image": latest_entry.entry_image.url
                if latest_entry.entry_image
                else None,
                "exit_image": latest_entry.exit_image.url
                if latest_entry.exit_image
                else None,
            }
        else:
            return None

    @database_sync_to_async
    def delete_entry(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)
            entry.delete()
            return {"success": True, "entry_id": entry_id}
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    @database_sync_to_async
    def get_latest_unpaid_entry(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get the latest unpaid entry that has exited today
        # This includes vehicles that entered yesterday but exited today
        latest_entry = (
            VehicleEntry.objects.filter(
                exit_time__gte=start_datetime,
                exit_time__lte=end_datetime,
                is_paid=False,
                is_error=False,  # Xatolik belgilanganlarni chiqarib tashlash
                exit_time__isnull=False,
            )
            .order_by("-exit_time")
            .first()
        )

        if latest_entry:
            # Ensure timezone-aware formatting
            entry_time = latest_entry.entry_time
            exit_time = latest_entry.exit_time

            return {
                "id": latest_entry.id,
                "number_plate": latest_entry.number_plate,
                "entry_time": entry_time.strftime("%H:%M"),
                "exit_time": exit_time.strftime("%H:%M"),
                "total_amount": latest_entry.total_amount or 0,
                "duration_hours": (exit_time - entry_time).total_seconds() / 3600,
                "entry_image": latest_entry.entry_image.url
                if latest_entry.entry_image
                else None,
                "exit_image": latest_entry.exit_image.url
                if latest_entry.exit_image
                else None,
            }
        else:
            return None

    @database_sync_to_async
    def get_unpaid_entries(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get unpaid entries that have exited today
        # This includes vehicles that entered yesterday but exited today
        unpaid_entries = VehicleEntry.objects.filter(
            exit_time__gte=start_datetime,
            exit_time__lte=end_datetime,
            is_paid=False,
            exit_time__isnull=False,
        ).order_by("-exit_time")

        entries_data = []
        for entry in unpaid_entries:
            # Ensure timezone-aware formatting
            entry_time = entry.entry_time
            exit_time = entry.exit_time

            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M"),
                    "total_amount": entry.total_amount or 0,
                    "duration_hours": (exit_time - entry_time).total_seconds() / 3600,
                }
            )

        return entries_data

    @database_sync_to_async
    def get_receipt(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)

            if not entry.is_paid:
                return {"success": False, "error": "Entry is not paid"}

            # Ensure timezone-aware formatting
            entry_time = entry.entry_time
            exit_time = entry.exit_time

            receipt_data = {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry_time.strftime("%H:%M"),
                "exit_time": exit_time.strftime("%H:%M") if exit_time else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "duration_hours": (exit_time - entry_time).total_seconds() / 3600
                if exit_time
                else 0,
            }

            return {"success": True, "receipt": receipt_data}
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    async def handle_get_receipt(self, entry_id):
        result = await self.get_receipt(entry_id)
        await self.send(text_data=json.dumps({"type": "receipt_data", "data": result}))

    async def handle_delete_entry(self, entry_id):
        result = await self.delete_entry(entry_id)
        await self.send(text_data=json.dumps({"type": "entry_deleted", "data": result}))

    async def handle_clear_exit_time(self, entry_id):
        result = await self.clear_exit_time(entry_id)

        if result["success"]:
            # Send clear exit time update to client
            await self.send(
                text_data=json.dumps({"type": "exit_time_cleared", "data": result})
            )

            # Send real-time updates to all clients
            await self.channel_layer.group_send(
                "home_updates",
                {
                    "type": "broadcast_update",
                    "statistics": result["statistics"],
                    "vehicle_entries": result["vehicle_entries"],
                    "action": "exit_time_cleared",
                    "entry_id": entry_id,
                },
            )

            # Send latest unpaid entry update
            if result["latest_unpaid_entry"]:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "latest_unpaid_entry_update",
                            "data": result["latest_unpaid_entry"],
                        }
                    )
                )
        else:
            await self.send(
                text_data=json.dumps({"type": "clear_exit_time_error", "data": result})
            )

    async def send_statistics(self, date_str):
        stats = await self.get_statistics(date_str)
        await self.send(
            text_data=json.dumps({"type": "statistics_update", "data": stats})
        )

    async def send_vehicle_entries(self, date_str, search_query=""):
        entries = await self.get_vehicle_entries(date_str, search_query)
        await self.send(
            text_data=json.dumps({"type": "vehicle_entries_update", "data": entries})
        )

    async def send_latest_unpaid_entry(self, date_str):
        entry = await self.get_latest_unpaid_entry(date_str)
        await self.send(
            text_data=json.dumps({"type": "latest_unpaid_entry_update", "data": entry})
        )

    async def send_unpaid_entries(self, date_str):
        entries = await self.get_unpaid_entries(date_str)
        await self.send(
            text_data=json.dumps({"type": "unpaid_entries_update", "data": entries})
        )

    async def handle_mark_as_paid(self, entry_id):
        result = await self.mark_as_paid(entry_id)

        if result["success"]:
            # Send payment update to client
            await self.send(
                text_data=json.dumps({"type": "payment_update", "data": result})
            )

            # Send real-time updates to all clients
            await self.channel_layer.group_send(
                "home_updates",
                {
                    "type": "broadcast_update",
                    "statistics": result["statistics"],
                    "vehicle_entries": result["vehicle_entries"],
                    "action": "payment_completed",
                    "entry_id": entry_id,
                },
            )

            # Send latest unpaid entry update
            if result["latest_unpaid_entry"]:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "latest_unpaid_entry_update",
                            "data": result["latest_unpaid_entry"],
                        }
                    )
                )
            else:
                await self.send(
                    text_data=json.dumps(
                        {"type": "latest_unpaid_entry_update", "data": None}
                    )
                )
        else:
            await self.send(
                text_data=json.dumps({"type": "payment_update", "data": result})
            )

    def print_receipt_to_xprinter_sync(self, entry_id):
        """Synchronous version of print_receipt_to_xprinter for use in mark_as_paid"""
        try:
            entry = VehicleEntry.objects.get(id=entry_id)

            # Calculate duration
            if entry.exit_time and entry.entry_time:
                total_seconds = int(
                    (entry.exit_time - entry.entry_time).total_seconds()
                )
                if total_seconds < 3600:
                    minutes = (total_seconds + 59) // 60  # ceil to next minute
                    duration_text = f"{minutes} daqiqa"
                elif total_seconds < 86400:
                    hours = total_seconds // 3600
                    remaining_seconds = total_seconds % 3600
                    minutes = (remaining_seconds + 59) // 60  # ceil minutes
                    if minutes == 60:
                        hours += 1
                        minutes = 0
                    if minutes == 0:
                        duration_text = f"{hours} soat"
                    else:
                        duration_text = f"{hours} soat {minutes} daqiqa"
                else:
                    days = total_seconds // 86400
                    remaining_seconds = total_seconds % 86400
                    hours = remaining_seconds // 3600
                    remaining_seconds = remaining_seconds % 3600
                    minutes = (remaining_seconds + 59) // 60  # ceil minutes
                    if minutes == 60:
                        hours += 1
                        minutes = 0
                    if hours == 24:
                        days += 1
                        hours = 0
                    if hours == 0 and minutes == 0:
                        duration_text = f"{days} kun"
                    elif minutes == 0:
                        duration_text = f"{days} kun {hours} soat"
                    else:
                        duration_text = f"{days} kun {hours} soat {minutes} daqiqa"
            else:
                duration_text = "0 daqiqa"

            # Import utils dan print_receipt funksiyasini
            from .utils import print_receipt

            # Chek chiqarish uchun ma'lumotlarni tayyorlash
            exit_time_str = (
                entry.exit_time.strftime("%Y-%m-%d %H:%M") if entry.exit_time else "--"
            )
            payment_amount_str = (
                f"{int(entry.total_amount)} so'm" if entry.total_amount else "0 so'm"
            )

            # print_receipt funksiyasini chaqirish
            success = print_receipt(
                printer_name=None,
                company_name="IDSOFT GROUP",
                project_name="SMART AUTO PARK",
                location="URGANCH MARKAZIY DEHQON BOZORI",
                address="7-SHAX JIZZAX KO'CHA 1-UY",
                car_number=entry.number_plate,
                entry_time=entry.entry_time.strftime("%Y-%m-%d %H:%M"),
                exit_time=exit_time_str,
                duration=duration_text,
                payment_amount=payment_amount_str,
                thank_message="Tashrifingiz uchun Rahmat!",
            )

            if success:
                return {
                    "success": True,
                    "message": f"Chek {entry.number_plate} uchun muvaffaqiyatli chiqarildi",
                }
            else:
                return {"success": False, "error": "Chek chiqarishda xatolik yuz berdi"}

        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry topilmadi"}
        except Exception as e:
            return {"success": False, "error": f"Xatolik: {str(e)}"}

    @database_sync_to_async
    def print_receipt_to_xprinter(self, entry_id):
        """Print receipt using utils.print_receipt function"""
        return self.print_receipt_to_xprinter_sync(entry_id)

    async def handle_print_receipt(self, entry_id):
        """Handle print receipt request"""
        result = await self.print_receipt_to_xprinter(entry_id)
        await self.send(
            text_data=json.dumps({"type": "print_receipt_result", "data": result})
        )

    async def handle_print_simple_receipt(self, entry_id):
        """Handle print simple receipt request - same as print_receipt"""
        result = await self.print_receipt_to_xprinter(entry_id)
        await self.send(
            text_data=json.dumps(
                {"type": "print_simple_receipt_result", "data": result}
            )
        )

    @database_sync_to_async
    def find_xprinter_usb_ids(self):
        """Find XPrinter USB VendorID and ProductID"""
        try:
            from escpos.printer import Usb
            import usb.core

            # Common XPrinter USB identifiers
            common_ids = [
                (0x1FC9, 0x2016),  # Example ID
                (0x0483, 0x5743),  # Another common ID
                (0x0483, 0x5740),  # Another common ID
                (0x0483, 0x5741),  # Another common ID
                (0x0483, 0x5742),  # Another common ID
            ]

            found_printers = []

            for vendor_id, product_id in common_ids:
                try:
                    # Try to find the device
                    device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
                    if device:
                        # Try to create printer instance (ensures USB access works)
                        Usb(vendor_id, product_id)
                        found_printers.append(
                            {
                                "vendor_id": vendor_id,
                                "product_id": product_id,
                                "status": "available",
                            }
                        )
                        print(
                            f"✅ Found XPrinter: VendorID=0x{vendor_id:04x}, ProductID=0x{product_id:04x}"
                        )
                    else:
                        found_printers.append(
                            {
                                "vendor_id": vendor_id,
                                "product_id": product_id,
                                "status": "not_found",
                            }
                        )
                except Exception as e:
                    found_printers.append(
                        {
                            "vendor_id": vendor_id,
                            "product_id": product_id,
                            "status": "error",
                            "error": str(e),
                        }
                    )
                    print(
                        f"❌ Error testing VendorID=0x{vendor_id:04x}, ProductID=0x{product_id:04x}: {e}"
                    )

            return {"success": True, "printers": found_printers}

        except ImportError:
            return {
                "success": False,
                "error": "python-escpos yoki usb kutubxonasi yo'q",
            }
        except Exception as e:
            return {"success": False, "error": f"USB qidiruv xatolik: {str(e)}"}

    async def handle_find_xprinter(self):
        """Handle find XPrinter request"""
        result = await self.find_xprinter_usb_ids()
        await self.send(
            text_data=json.dumps({"type": "xprinter_search_result", "data": result})
        )

    @database_sync_to_async
    def test_xprinter_connection(self):
        """Test XPrinter connection and print test receipt"""
        try:
            from escpos.printer import Usb
            from django.conf import settings

            vendor_id = getattr(settings, "XPRINTER_VENDOR_ID", 0x1FC9)
            product_id = getattr(settings, "XPRINTER_PRODUCT_ID", 0x2016)
            timeout = getattr(settings, "XPRINTER_TIMEOUT", 1000)

            # Create printer instance
            p = Usb(vendor_id, product_id, timeout=timeout)

            # Print test receipt
            p.text("=== TEST CHEK ===\n")
            p.text("SMART AUTOPARK\n")
            p.text("XPrinter test\n")
            p.text(f"Vaqt: {timezone.now().strftime('%d.%m.%Y %H:%M')}\n")
            p.text("Bu test chek\n")
            p.text("XPrinter ishlayapti!\n")
            p.text("================\n")

            # Cut the paper (ESC/POS cut command)
            p.cut()

            return {
                "success": True,
                "message": "Test chek USB orqali XPrinter dan chiqdi",
            }

        except ImportError:
            return {"success": False, "error": "python-escpos kutubxonasi yo'q"}
        except Exception as e:
            return {"success": False, "error": f"XPrinter test xatolik: {str(e)}"}

    async def handle_test_xprinter(self):
        """Handle test XPrinter request"""
        result = await self.test_xprinter_connection()
        await self.send(
            text_data=json.dumps({"type": "xprinter_test_result", "data": result})
        )
