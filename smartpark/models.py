from asyncio import FastChildWatcher
from email.policy import default
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
import uuid


def generate_uuid_hex():
    """Generate a punctuation-free UUID string (10 hex chars)."""
    return uuid.uuid4().hex[:10]


class Role(models.TextChoices):
    OPERATOR = "operator"
    ADMIN = "admin"


class CustomUser(AbstractUser):
    image = models.ImageField(upload_to="users/", blank=True, null=True)
    role = models.CharField(max_length=50, default=Role.OPERATOR)

    def __str__(self):
        return self.username

    def hesh_password(self):
        password = self.password
        self.password = make_password(password)
        self.save(update_fields=["password"])
        return True

    class Meta:
        db_table = "custom_users"
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"


class VehicleEntry(models.Model):
    number_plate = models.CharField(max_length=15)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(blank=True, null=True)
    entry_image = models.ImageField(upload_to="entries/")
    exit_image = models.ImageField(upload_to="exits/", blank=True, null=True)
    total_amount = models.IntegerField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    uuid = models.CharField(
        max_length=10,
        default=generate_uuid_hex,
        editable=False,
        unique=True,
        validators=[
            RegexValidator(r"^[0-9a-fA-F]{10}$", "UUID 10 ta harf/son bo'lishi kerak")
        ],
    )
    is_error=models.BooleanField(default=False)
    error_massage=models.CharField(max_length=255,blank=True,null=True)
    
    def __str__(self):
        # Ensure timezone-aware formatting
        entry_time = self.entry_time
        return f"{self.number_plate} - {entry_time.strftime('%Y-%m-%d %H:%M')}"

    def calculate_amount(self):
        """Parking fee hisoblash:
        - 10 daqiqa bepul
        - 10 daqiqadan 1 soatgacha: 4000 so'm
        - 1 soatdan keyin: har 15 minutga 1000 so'm qo'shiladi 2 soatgacha
        - 2 soatdan keyin: yana 1 sekund o`tsa ham 4000 so`m qoshiladi toki 5 soatga yetguncha yani 15 minutlik intervallarga bo`linmaydi
        - 5 soatgacha (20000 so'mgacha) shunday hisoblanadi
        - 5 soatdan 24 soatgacha: faqat 5 soat uchun pul (20000 so'm)
        - 24 soatdan 1 sekund o'tsa ham: 20000 + 20000 = 40000 so'm
        - 48 soatdan 1 sekund o'tsa ham: 20000 + 20000 + 20000 = 60000 so'm
        """
        if not self.exit_time:
            return 0

        from config.settings import HOUR_PRICE, FREE_MINUTES

        DAILY_LIMIT = 5 * HOUR_PRICE  # 5 soat uchun maksimum (20000)
        QUARTER_HOUR_PRICE = 1000  # 15 minut uchun narx
        QUARTER_HOUR_MINUTES = 15  # 15 daqiqa

        entry = self.entry_time
        exit = self.exit_time

        # Normalize to timezone-aware datetimes to avoid naive/aware subtraction
        if timezone.is_naive(entry):
            entry = timezone.make_aware(entry)
        else:
            entry = timezone.localtime(entry)

        if timezone.is_naive(exit):
            exit = timezone.make_aware(exit)
        else:
            exit = timezone.localtime(exit)

        # Umumiy davomiylik asosida oddiy hisoblash
        duration_seconds = (exit - entry).total_seconds()
        duration_minutes = duration_seconds / 60.0

        # 10 daqiqa va undan kam (shu jumladan 10 daqiqa) bepul
        if duration_minutes <= FREE_MINUTES:
            return 0

        # 10 daqiqadan 1 soatgacha (60 minutgacha): 4000 so'm
        if duration_minutes <= 60:
            return HOUR_PRICE  # 4000 so'm

        # 1 soatdan 2 soatgacha: har 15 minutga 1000 so'm qo'shiladi
        TWO_HOURS_MINUTES = 120  # 2 soat
        if duration_minutes <= TWO_HOURS_MINUTES:
            minutes_after_first_hour = duration_minutes - 60
            # 15 minutlik bloklar soni (yuqoriga yaxlitlab)
            quarter_hour_blocks = int(minutes_after_first_hour / QUARTER_HOUR_MINUTES)
            if minutes_after_first_hour % QUARTER_HOUR_MINUTES > 0:
                quarter_hour_blocks += 1
            # 1 soat uchun 4000 + har 15 minut uchun 1000
            return HOUR_PRICE + (quarter_hour_blocks * QUARTER_HOUR_PRICE)

        # 2 soatdan 5 soatgacha: har soat uchun 4000 so'm (1 sekund o'tsa ham yangi soat boshlangan deb hisoblanadi)
        # 2 soat uchun: 4000 (1 soat) + 4000 (1 soatdan 2 soatgacha 4*15min*1000) = 8000
        two_hours_amount = HOUR_PRICE + (4 * QUARTER_HOUR_PRICE)  # 4000 + 4000 = 8000

        # 2 soatdan keyingi qism: har soat uchun 4000 so'm (1 sekund o'tsa ham yangi soat boshlangan)
        hours_after_two_hours = (duration_minutes - TWO_HOURS_MINUTES) / 60.0
        # Har soat uchun 4000 so'm, lekin 1 sekund o'tsa ham yangi soat boshlangan deb hisoblanadi (ceil)
        import math

        additional_hours = math.ceil(
            hours_after_two_hours
        )  # 1 sekund o'tsa ham yangi soat

        total_amount = two_hours_amount + (additional_hours * HOUR_PRICE)

        # 5 soatgacha (20000 so'mgacha) limit
        if total_amount > DAILY_LIMIT:
            total_amount = DAILY_LIMIT

        # 5 soatdan keyin: 24 soatgacha faqat 5 soat uchun pul (20000 so'm)
        # 24 soatdan 1 sekund o'tsa ham har 24 soat uchun 20000 qo'shiladi
        seconds_in_day = 24 * 60 * 60
        if duration_seconds > 5 * 60 * 60:  # 5 soatdan oshsa
            # 5 soatdan 24 soatgacha: 20000 so'm (faqat 5 soat uchun)
            if duration_seconds < seconds_in_day:
                return DAILY_LIMIT  # 20000 so'm
            else:
                # 24 soatdan 1 sekund o'tsa ham: 20000 + 20000 = 40000
                # 48 soatdan 1 sekund o'tsa ham: 20000 + 20000 + 20000 = 60000
                full_days = int(
                    duration_seconds // seconds_in_day
                )  # necha marta 24 soat to'ldi (floor)
                return DAILY_LIMIT + (
                    full_days * DAILY_LIMIT
                )  # 20000 + (full_days * 20000)

        return total_amount

    def calculate_amount_for_exit_time(self, exit_time):
        """Parking fee hisoblash:
        - 10 daqiqa bepul
        - 10 daqiqadan 1 soatgacha: 4000 so'm
        - 1 soatdan keyin: har 15 minutga 1000 so'm qo'shiladi 2 soatgacha
        - 2 soatdan keyin: yana 1 sekund o`tsa ham 4000 so`m qoshiladi toki 5 soatga yetguncha yani 15 minutlik intervallarga bo`linmaydi
        - 5 soatgacha (20000 so'mgacha) shunday hisoblanadi
        - 5 soatdan 24 soatgacha: faqat 5 soat uchun pul (20000 so'm)
        - 24 soatdan 1 sekund o'tsa ham: 20000 + 20000 = 40000 so'm
        - 48 soatdan 1 sekund o'tsa ham: 20000 + 20000 + 20000 = 60000 so'm
        """
        from config.settings import HOUR_PRICE, FREE_MINUTES

        DAILY_LIMIT = 5 * HOUR_PRICE  # 5 soat uchun maksimum (20000)
        QUARTER_HOUR_PRICE = 1000  # 15 minut uchun narx
        QUARTER_HOUR_MINUTES = 15  # 15 daqiqa

        entry = self.entry_time
        exit = exit_time

        # Normalize to timezone-aware datetimes to avoid naive/aware subtraction
        if timezone.is_naive(entry):
            entry = timezone.make_aware(entry)
        else:
            entry = timezone.localtime(entry)

        if timezone.is_naive(exit):
            exit = timezone.make_aware(exit)
        else:
            exit = timezone.localtime(exit)

        # Umumiy davomiylik asosida oddiy hisoblash
        duration_seconds = (exit - entry).total_seconds()
        duration_minutes = duration_seconds / 60.0

        # 10 daqiqa va undan kam (shu jumladan 10 daqiqa) bepul
        if duration_minutes <= FREE_MINUTES:
            return 0

        # 10 daqiqadan 1 soatgacha (60 minutgacha): 4000 so'm
        if duration_minutes <= 60:
            return HOUR_PRICE  # 4000 so'm

        # 1 soatdan 2 soatgacha: har 15 minutga 1000 so'm qo'shiladi
        TWO_HOURS_MINUTES = 120  # 2 soat
        if duration_minutes <= TWO_HOURS_MINUTES:
            minutes_after_first_hour = duration_minutes - 60
            # 15 minutlik bloklar soni (yuqoriga yaxlitlab)
            quarter_hour_blocks = int(minutes_after_first_hour / QUARTER_HOUR_MINUTES)
            if minutes_after_first_hour % QUARTER_HOUR_MINUTES > 0:
                quarter_hour_blocks += 1
            # 1 soat uchun 4000 + har 15 minut uchun 1000
            return HOUR_PRICE + (quarter_hour_blocks * QUARTER_HOUR_PRICE)

        # 2 soatdan 5 soatgacha: har soat uchun 4000 so'm (1 sekund o'tsa ham yangi soat boshlangan deb hisoblanadi)
        # 2 soat uchun: 4000 (1 soat) + 4000 (1 soatdan 2 soatgacha 4*15min*1000) = 8000
        two_hours_amount = HOUR_PRICE + (4 * QUARTER_HOUR_PRICE)  # 4000 + 4000 = 8000

        # 2 soatdan keyingi qism: har soat uchun 4000 so'm (1 sekund o'tsa ham yangi soat boshlangan)
        hours_after_two_hours = (duration_minutes - TWO_HOURS_MINUTES) / 60.0
        # Har soat uchun 4000 so'm, lekin 1 sekund o'tsa ham yangi soat boshlangan deb hisoblanadi (ceil)
        import math

        additional_hours = math.ceil(
            hours_after_two_hours
        )  # 1 sekund o'tsa ham yangi soat

        total_amount = two_hours_amount + (additional_hours * HOUR_PRICE)

        # 5 soatgacha (20000 so'mgacha) limit
        if total_amount > DAILY_LIMIT:
            total_amount = DAILY_LIMIT

        # 5 soatdan keyin: 24 soatgacha faqat 5 soat uchun pul (20000 so'm)
        # 24 soatdan 1 sekund o'tsa ham har 24 soat uchun 20000 qo'shiladi
        seconds_in_day = 24 * 60 * 60
        if duration_seconds > 5 * 60 * 60:  # 5 soatdan oshsa
            # 5 soatdan 24 soatgacha: 20000 so'm (faqat 5 soat uchun)
            if duration_seconds < seconds_in_day:
                return DAILY_LIMIT  # 20000 so'm
            else:
                # 24 soatdan 1 sekund o'tsa ham: 20000 + 20000 = 40000
                # 48 soatdan 1 sekund o'tsa ham: 20000 + 20000 + 20000 = 60000
                full_days = int(
                    duration_seconds // seconds_in_day
                )  # necha marta 24 soat to'ldi (floor)
                return DAILY_LIMIT + (
                    full_days * DAILY_LIMIT
                )  # 20000 + (full_days * 20000)

        return total_amount

    def mark_as_paid(self):
        """Mark this entry as paid"""
        self.is_paid = True
        self.save()

    class Meta:
        db_table = "vehicle_entries"
        verbose_name = "Vehicle Entry"
        verbose_name_plural = "Vehicle Entries"


class Cars(models.Model):
    number_plate = models.CharField(max_length=15)
    is_free = models.BooleanField(default=False)
    is_special_taxi = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Lavozim (bepul avtomobillar uchun)",
    )
    license_file = models.FileField(
        upload_to="licenses/",
        blank=True,
        null=True,
        help_text="Litsenziya fayli (maxsus taksi uchun)",
    )

    def __str__(self):
        status = []
        if self.is_free:
            status.append("Bepul")
        if self.is_special_taxi:
            status.append("Maxsus taksi")
        if self.is_blocked:
            status.append("Bloklangan")

        status_str = f" ({', '.join(status)})" if status else ""
        return f"{self.number_plate}{status_str}"

    class Meta:
        db_table = "cars"
        verbose_name = "Car"
        verbose_name_plural = "Cars"
