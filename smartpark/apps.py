from django.apps import AppConfig
from django.utils import timezone
from datetime import timedelta
import threading
import time
import django


class SmartparkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "smartpark"

    def ready(self):
        """Import signals when the app is ready"""
        import smartpark.signals

        # Worker 1 marta ishga tushishi uchun
        if hasattr(self, "auto_clean_started"):
            return
        self.auto_clean_started = True

        # Background thread yaratamiz
        cleaner_thread = threading.Thread(target=self.start_auto_cleaner, daemon=True)
        cleaner_thread.start()

    def start_auto_cleaner(self):
        """Har 1 soatda 1 haftadan oshgan chiqmagan mashinalarni o‘chiradi"""
        django.setup()

        # ⚠️ IMPORT FAQAT SHU YERDA BO‘LISHI SHART!
        from .models import VehicleEntry

        while True:
            try:
                one_week_ago = timezone.now() - timedelta(days=7)

                # exit_time NULL (chiqmagan mashina)
                # entry_time 1 haftadan eski
                deleted_count, _ = VehicleEntry.objects.filter(
                    exit_time__isnull=True, entry_time__lte=one_week_ago
                ).delete()

                print(f"[AUTO CLEANER] Deleted {deleted_count} old vehicle entries")

            except Exception as e:
                print("[AUTO CLEANER ERROR]:", e)

            # Har 1 soatda ishlaydi (3600 = 1 hour)
            time.sleep(3600)
