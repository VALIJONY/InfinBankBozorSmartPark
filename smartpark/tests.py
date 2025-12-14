from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from .models import VehicleEntry
from config.settings import HOUR_PRICE
from django.utils.timezone import make_aware

# Test Constants
DAILY_LIMIT = 5 * HOUR_PRICE
TEST_NUMBER_PLATE = "10A777AA"


class TestVehicleEntryAmountCalculation(TestCase):
    """VehicleEntry narx hisoblash testlari - Database yaratmasdan"""

    def test_no_exit_time_returns_zero(self):
        """Chiqish vaqti yo'q bo'lsa 0 qaytaradi"""
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=timezone.make_aware(datetime(2025, 8, 30, 8)),
        )
        self.assertEqual(entry.calculate_amount(), 0)

    def test_10_minutes_free(self):
        """10 daqiqa bepul"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:10 (10 daqiqa)
        # Hisoblash: 10 daqiqa <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 0)

    def test_11_minutes_one_hour(self):
        """11 daqiqa - 1 soat hisobida"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:11 (11 daqiqa)
        # Hisoblash: 11 daqiqa > 10 daqiqa, 11/60 = 0.183 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 11)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_one_hour_one_minute_two_hours(self):
        """1 soat 1 daqiqa - 2 soat hisobida"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 09:01 (1 soat 1 daqiqa)
        # Hisoblash: 61 daqiqa > 10 daqiqa, 61/60 = 1.017 soat -> 2 soat = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)

    def test_one_hour_one_second_two_hours(self):
        """1 soat 1 soniya - 2 soat hisobida"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 09:00:01 (1 soat 1 soniya)
        # Hisoblash: 60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 2 soat = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)

    def test_exactly_one_hour(self):
        """Aniq bir soat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 09:00:00 (1 soat)
        # Hisoblash: 60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_exactly_five_hours(self):
        """Aniq besh soat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 13:00:00 (5 soat)
        # Hisoblash: 300 daqiqa > 10 daqiqa, 300/60 = 5.0 soat -> 5 soat = 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 13, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_exactly_six_hours_limit(self):
        """Aniq olti soat (limitdan oshadi)"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 14:00:00 (6 soat)
        # Hisoblash: 360 daqiqa > 10 daqiqa, 360/60 = 6.0 soat -> 6 soat = 24000, lekin limit 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 14, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_2_hours_30_minutes_3_hours(self):
        """2 soat 30 daqiqa - 3 soat hisobida"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 10:30 (2 soat 30 daqiqa)
        # Hisoblash: 150 daqiqa > 10 daqiqa, 150/60 = 2.5 soat -> 3 soat = 12000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 10, 30)),
        )
        self.assertEqual(entry.calculate_amount(), 12000)

    def test_4_hours_45_minutes_5_hours(self):
        """4 soat 45 daqiqa - 5 soat hisobida"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 12:45 (4 soat 45 daqiqa)
        # Hisoblash: 285 daqiqa > 10 daqiqa, 285/60 = 4.75 soat -> 5 soat = 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 12, 45)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_5_hours_1_minute_limit(self):
        """5 soat 1 daqiqa - 6 soat hisobida, lekin limit"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 13:01 (5 soat 1 daqiqa)
        # Hisoblash: 301 daqiqa > 10 daqiqa, 301/60 = 5.017 soat -> 6 soat = 24000, lekin limit 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 13, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_cross_midnight_short(self):
        """Yarim tunni kesib o'tish qisqa"""
        # Vaqt: 2025-08-30 23:00 -> 2025-08-31 01:00 (2 soat)
        # Hisoblash:
        # 1-kun: 23:00 -> 23:59 (59 daqiqa > 10 daqiqa, 59/60 = 0.983 soat -> 1 soat = 4000 so'm)
        # 2-kun: 00:00 -> 01:00 (60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm)
        # Jami = 4000 + 4000 = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 23)),
            exit_time=make_aware(datetime(2025, 8, 31, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)

    def test_entry_evening_exit_next_morning(self):
        """Kechki kirish, ertalab chiqish"""
        # Vaqt: 2025-08-30 20:00 -> 2025-08-31 07:00 (11 soat)
        # Hisoblash:
        # 1-kun: 20:00 -> 23:59 (239 daqiqa > 10 daqiqa, 239/60 = 3.983 soat -> 4 soat = 16000 so'm)
        # 2-kun: 00:00 -> 07:00 (420 daqiqa > 10 daqiqa, 420/60 = 7.0 soat -> 7 soat = 28000, lekin limit 20000 so'm)
        # Jami = 16000 + 20000 = 36000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 20)),
            exit_time=make_aware(datetime(2025, 8, 31, 7)),
        )
        self.assertEqual(entry.calculate_amount(), 36000)

    def test_two_days_simple(self):
        """Ikki kun oddiy"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-31 10:00 (26 soat)
        # Hisoblash:
        # 1-kun: 08:00 -> 23:59 (959 daqiqa > 10 daqiqa, 959/60 = 15.983 soat -> 16 soat = 64000, lekin limit 20000 so'm)
        # 2-kun: 00:00 -> 10:00 (600 daqiqa > 10 daqiqa, 600/60 = 10.0 soat -> 10 soat = 40000, lekin limit 20000 so'm)
        # Jami = 20000 + 20000 = 40000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 31, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 40000)

    def test_three_days_partial_last_day(self):
        """Uch kun, oxirgi kunda qisman"""
        # Vaqt: 2025-08-30 08:00 -> 2025-09-01 02:00 (42 soat)
        # Hisoblash:
        # 1-kun: 08:00 -> 23:59 (959 daqiqa > 10 daqiqa, 959/60 = 15.983 soat -> 16 soat = 64000, lekin limit 20000 so'm)
        # 2-kun: 00:00 -> 23:59 (24 soat = limit 20000 so'm)
        # 3-kun: 00:00 -> 02:00 (120 daqiqa > 10 daqiqa, 120/60 = 2.0 soat -> 2 soat = 8000 so'm)
        # Jami = 20000 + 20000 + 8000 = 48000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 9, 1, 2)),
        )
        self.assertEqual(entry.calculate_amount(), 48000)

    def test_cross_midnight_first_day_free(self):
        """Yarim tunni kesib o'tish, birinchi kun bepul"""
        # Vaqt: 2025-08-30 23:50 -> 2025-08-31 01:00 (1 soat 10 daqiqa)
        # Hisoblash:
        # 1-kun: 23:50 -> 23:59 (9 daqiqa <= 10 daqiqa = bepul)
        # 2-kun: 00:00 -> 01:00 (60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm)
        # Jami = 0 + 4000 = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 23, 50)),
            exit_time=make_aware(datetime(2025, 8, 31, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_cross_midnight_last_day_free(self):
        """Yarim tunni kesib o'tish, oxirgi kun bepul"""
        # Vaqt: 2025-08-30 23:00 -> 2025-08-31 00:10 (1 soat 10 daqiqa)
        # Hisoblash:
        # 1-kun: 23:00 -> 23:59 (59 daqiqa > 10 daqiqa, 59/60 = 0.983 soat -> 1 soat = 4000 so'm)
        # 2-kun: 00:00 -> 00:10 (10 daqiqa <= 10 daqiqa = bepul)
        # Jami = 4000 + 0 = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 23)),
            exit_time=make_aware(datetime(2025, 8, 31, 0, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_cross_midnight_both_days_free(self):
        """Yarim tunni kesib o'tish, ikkala kun ham bepul"""
        # Vaqt: 2025-08-30 23:50 -> 2025-08-31 00:10 (20 daqiqa)
        # Hisoblash:
        # 1-kun: 23:50 -> 23:59 (9 daqiqa <= 10 daqiqa = bepul)
        # 2-kun: 00:00 -> 00:10 (10 daqiqa <= 10 daqiqa = bepul)
        # Jami = 0 + 0 = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 23, 50)),
            exit_time=make_aware(datetime(2025, 8, 31, 0, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 0)

    def test_multiple_days_with_free_periods(self):
        """Bir necha kun, bepul vaqtlar bilan"""
        # Vaqt: 2025-08-30 23:50 -> 2025-09-01 00:10 (2 kun 10 daqiqa)
        # Hisoblash:
        # 1-kun: 23:50 -> 23:59 (9 daqiqa <= 10 daqiqa = bepul)
        # 2-kun: 00:00 -> 23:59 (24 soat = limit 20000 so'm)
        # 3-kun: 00:00 -> 00:10 (10 daqiqa <= 10 daqiqa = bepul)
        # Jami = 0 + 20000 + 0 = 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 23, 50)),
            exit_time=make_aware(datetime(2025, 9, 1, 0, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_exact_10_minutes_edge_case(self):
        """Aniq 10 daqiqa chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 08:10:00 (10 daqiqa)
        # Hisoblash: 10 daqiqa <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 10, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 0)

    def test_exact_11_minutes_edge_case(self):
        """Aniq 11 daqiqa chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 08:11:00 (11 daqiqa)
        # Hisoblash: 11 daqiqa > 10 daqiqa, 11/60 = 0.183 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 11, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_exact_one_hour_edge_case(self):
        """Aniq bir soat chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 09:00:00 (1 soat)
        # Hisoblash: 60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_one_hour_one_second_edge_case(self):
        """1 soat 1 soniya chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 09:00:01 (1 soat 1 soniya)
        # Hisoblash: 3601 soniya > 10 daqiqa, 3601/3600 = 1.0003 soat -> 2 soat = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)

    def test_exact_five_hours_edge_case(self):
        """Aniq besh soat chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 13:00:00 (5 soat)
        # Hisoblash: 300 daqiqa > 10 daqiqa, 300/60 = 5.0 soat -> 5 soat = 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 13, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)

    def test_five_hours_one_second_edge_case(self):
        """5 soat 1 soniya chekka holat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 13:00:01 (5 soat 1 soniya)
        # Hisoblash: 18001 soniya > 10 daqiqa, 18001/3600 = 5.0003 soat -> 6 soat = 24000, lekin limit 20000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 13, 0, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 20000)


class TestVehicleEntryEdgeCases(TestCase):
    """VehicleEntry chekka holatlar testlari - Database yaratmasdan"""

    def test_very_short_stay_30_seconds(self):
        """Juda qisqa vaqt - 30 soniya bepul"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 08:00:30 (30 soniya)
        # Hisoblash: 30 soniya <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 0, 30)),  # 30 soniya
        )
        self.assertEqual(entry.calculate_amount(), 0)  # Bepul

    def test_edge_case_one_minute(self):
        """Bir daqiqa chekka holat - bepul"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:01 (1 daqiqa)
        # Hisoblash: 1 daqiqa <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 0)  # Bepul

    def test_edge_case_10_minutes(self):
        """10 daqiqa chekka holat - bepul"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:10 (10 daqiqa)
        # Hisoblash: 10 daqiqa <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 10)),
        )
        self.assertEqual(entry.calculate_amount(), 0)  # Bepul

    def test_edge_case_11_minutes(self):
        """11 daqiqa chekka holat - 1 soat"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:11 (11 daqiqa)
        # Hisoblash: 11 daqiqa > 10 daqiqa, 11/60 = 0.183 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 11)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)  # 1 soat

    def test_cross_month_boundary(self):
        """Oyni kesib o'tish"""
        # Vaqt: 2025-08-31 23:00:00 -> 2025-09-01 01:00:00 (2 soat)
        # Hisoblash:
        # 1-kun: 23:00 -> 23:59 (59 daqiqa > 10 daqiqa, 59/60 = 0.983 soat -> 1 soat = 4000 so'm)
        # 2-kun: 00:00 -> 01:00 (60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm)
        # Jami = 4000 + 4000 = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 31, 23, 0, 0)),
            exit_time=make_aware(datetime(2025, 9, 1, 1, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)  # 2 soat

    def test_cross_year_boundary(self):
        """Yilni kesib o'tish"""
        # Vaqt: 2024-12-31 23:00:00 -> 2025-01-01 01:00:00 (2 soat)
        # Hisoblash:
        # 1-kun: 23:00 -> 23:59 (59 daqiqa > 10 daqiqa, 59/60 = 0.983 soat -> 1 soat = 4000 so'm)
        # 2-kun: 00:00 -> 01:00 (60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm)
        # Jami = 4000 + 4000 = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2024, 12, 31, 23, 0, 0)),
            exit_time=make_aware(datetime(2025, 1, 1, 1, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)  # 2 soat

    def test_very_long_stay_10_days(self):
        """Juda uzoq vaqt - 10 kun"""
        # Vaqt: 2025-08-30 08:00 -> 2025-09-09 08:00 (11 kun)
        # Hisoblash:
        # 1-kun: 08:00 -> 23:59 (959 daqiqa > 10 daqiqa, 959/60 = 15.983 soat -> 16 soat = 64000, lekin limit 20000 so'm)
        # 2-10 kun: har kuni 24 soat = har kuni 20000 so'm (9 kun * 20000 = 180000 so'm)
        # 11-kun: 00:00 -> 08:00 (480 daqiqa > 10 daqiqa, 480/60 = 8.0 soat -> 8 soat = 32000, lekin limit 20000 so'm)
        # Jami = 20000 + 180000 + 20000 = 220000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 9, 9, 8)),
        )
        # 10 kun * 20000 = 220000 (chunki 8-kundan 9-kungacha 11 kun)
        self.assertEqual(entry.calculate_amount(), 220000)

    def test_same_time_entry_exit(self):
        """Bir xil vaqtda kirish va chiqish"""
        # Vaqt: 2025-08-30 08:00 -> 2025-08-30 08:00 (0 daqiqa)
        # Hisoblash: 0 daqiqa <= 10 daqiqa (bepul) = 0 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 8)),
        )
        self.assertEqual(entry.calculate_amount(), 0)

    def test_59_minutes_59_seconds(self):
        """59 daqiqa 59 soniya - 1 soat (chunki 10 daqiqadan ko'p)"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 08:59:59 (59 daqiqa 59 soniya)
        # Hisoblash: 3599 soniya > 10 daqiqa, 3599/3600 = 0.9997 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 8, 59, 59)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_60_minutes_exact(self):
        """Aniq 60 daqiqa - 1 soat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 09:00:00 (60 daqiqa)
        # Hisoblash: 60 daqiqa > 10 daqiqa, 60/60 = 1.0 soat -> 1 soat = 4000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 0)),
        )
        self.assertEqual(entry.calculate_amount(), 4000)

    def test_60_minutes_1_second(self):
        """60 daqiqa 1 soniya - 2 soat"""
        # Vaqt: 2025-08-30 08:00:00 -> 2025-08-30 09:00:01 (60 daqiqa 1 soniya)
        # Hisoblash: 3601 soniya > 10 daqiqa, 3601/3600 = 1.0003 soat -> 2 soat = 8000 so'm
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8, 0, 0)),
            exit_time=make_aware(datetime(2025, 8, 30, 9, 0, 1)),
        )
        self.assertEqual(entry.calculate_amount(), 8000)


class TestVehicleEntryModel(TestCase):
    """VehicleEntry model testlari - Database yaratmasdan"""

    def test_vehicle_entry_str_representation(self):
        """VehicleEntry string ko'rinishi testi"""
        entry = VehicleEntry(
            number_plate=TEST_NUMBER_PLATE,
            entry_time=make_aware(datetime(2025, 8, 30, 8)),
            exit_time=make_aware(datetime(2025, 8, 30, 10)),
        )

        expected_str = f"{TEST_NUMBER_PLATE} - 2025-08-30 08:00"
        self.assertEqual(str(entry), expected_str)
