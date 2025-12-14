from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils import timezone
import json
from datetime import datetime
import logging
import requests
from django.utils.decorators import method_decorator
from .models import VehicleEntry
from django.conf import settings
import sys

# Logger yaratamiz
logger = logging.getLogger("unikassa_sync")


class UnikassaSyncService:
    """
    Unikassa /get/sync ni avtomatik chaqiradigan servis.
    """

    BASE_URL = "https://api.unikassa.uz/api/v1/integrate"

    @staticmethod
    def run_sync():
        url = f"{UnikassaSyncService.BASE_URL}/get/sync"
        payload = {"Fiscal": "ZZ000000000000"}
        try:
            r = requests.post(url, json=payload, timeout=10)
            result = r.json()
            if result is None:
                print("null")
            logger.info(f"SYNC OK | {datetime.now()} | URL={url} | Response={result}")
            return result

        except Exception as e:
            logger.error(f"SYNC ERROR | {datetime.now()} | URL={url} | Error={str(e)}")
            return None


@method_decorator(csrf_exempt, name="dispatch")
class SaleSend(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            price = data.get("price")
            amount = price
            price = str(int(price * 100))
            entry_id = data.get("id")
            paytype = data.get("paytype", "cash")  # Default to cash if not provided
            if not price:
                return JsonResponse({"error": "Price not provided"}, status=400)

            vat = price * 0.12

            now = timezone.now()
            time_str = now.strftime("%Y-%m-%d %H:%M:%S")

            BASE_URL = "https://api.unikassa.uz/api/v1/integrate"
            url = f"{BASE_URL}/send/sale"

            payload = {
                "Fiscal": "ZZ000000000000",
                "PayType": paytype.lower(),
                "PayInfo": None,
                "Receipt": {
                    "ExtraInfo": {
                        "CarNumber": "",
                        "CardNumber": "",
                        "CardType": 2,
                        "CashedOutFromCard": 0,
                        "PINFL": "",
                        "PPTID": "",
                        "PhoneNumber": "",
                        "QRPaymentID": "",
                        "QRPaymentProvider": 0,
                        "TIN": "",
                    },
                    "Items": [
                        {
                            "Amount": amount,
                            "Barcode": "3637718744639",
                            "CommissionInfo": None,
                            "Discount": 0,
                            "Label": "",
                            "Name": "Avtoturargoh xizmatlari",
                            "Other": 0,
                            "OwnerType": 0,
                            "PackageCode": "91058",
                            "Price": price,
                            "SPIC": "10199001007000000",
                            "Units": 1,
                            "VAT": vat,
                            "VATPercent": 12,
                        }
                    ],
                    "Location": {"Latitude": 41.554459, "Longitude": 60.622758},
                    "Operation": 0,
                    "ReceivedCard": price if paytype.lower() == "card" else 0,
                    "ReceivedCash": price if paytype.lower() == "cash" else 0,
                    "RefundInfo": None,
                    "Time": time_str,
                    "Type": 0,
                },
            }

            headers = {"Content-Type": "application/json"}
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            print_receipt_from_unikassa(r.json(), entry_id)
            return JsonResponse(r.json())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


if sys.platform.startswith("win"):
    import win32print  # type: ignore[import]
    import win32ui  # type: ignore[import]
    from PIL import Image, ImageDraw, ImageFont, ImageWin
    import qrcode


def print_receipt_from_unikassa(response_data, entry_id, printer_name=None):
    """
    response_data: SaleSend dan qaytgan dict
    Standart chek formatini yaratadi (rasmda ko'rsatilgan formatga mos)
    """

    # Agar Windows bo'lmasa, faqat log qilamiz va printerga yubormaymiz
    if not sys.platform.startswith("win"):
        logger.info(
            "print_receipt_from_unikassa: non-Windows platforma, chek faqat log qilinadi"
        )
        logger.info(f"Unikassa javobi: {response_data}")
        if entry_id:
            try:
                entry = VehicleEntry.objects.get(id=entry_id)
                entry.unikassacheck = False
                entry.save(update_fields=["unikassacheck"])
            except Exception as e:
                logger.warning(f"Entry holatini yangilashda xatolik (non-Windows): {e}")
        return False

    # Ma'lumotlarni olish va stringga o'tkazish
    qr_data = response_data.get("QRCodeURL", "")
    receipt_seq = str(response_data.get("ReceiptSeq", ""))
    date_time = str(response_data.get("DateTime", ""))
    fiscal_sign = str(response_data.get("FiscalSign", ""))

    # Qo'shimcha ma'lumotlar (agar mavjud bo'lsa)
    serial_number = str(response_data.get("SerialNumber", ""))
    fm_number = str(response_data.get("FMNumber", ""))
    rs_version = str(response_data.get("RSVersion", "SMARTONE 1.0.84"))

    # Kompaniya ma'lumotlari (settings yoki default)
    company_name = getattr(settings, "COMPANY_NAME", "SMART AUTO PARK")
    company_type = getattr(settings, "COMPANY_TYPE", "MAS'ULIYATI CHEKLANGAN JAMIYAT")
    company_region = getattr(settings, "COMPANY_REGION", "XORAZM VILOYATI")
    company_district = getattr(settings, "COMPANY_DISTRICT", "QO'SHKO'PIR TUMANI")
    company_address = getattr(
        settings, "COMPANY_ADDRESS", "KO'SHKO'PIR G., UL. SHAROF RASHIDOV, DOM 175"
    )
    company_stir = getattr(settings, "COMPANY_STIR", "310510032")

    # QR kod yaratish
    qr_img = None
    if qr_data and qr_data != "None" and str(qr_data).strip():
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=4,
                border=2,
            )
            qr.add_data(str(qr_data))
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
        except Exception as e:
            logger.error(f"QR kod yaratishda xatolik: {str(e)}")
            qr_img = None

    # Receipt rasmi - 80mm printer uchun (203 DPI = 576px width)
    width = 576
    # Dinamik balandlik (80mm uchun kattalashtirilgan)
    # QR koddan keyin katta bo'shliq uchun balandlikni oshirish
    base_height = 800  # Ko'proq joy kerak
    qr_height = 350 if qr_img else 0
    extra_space_after_qr = 400 if qr_img else 0  # QR koddan keyin qo'shimcha bo'shliq
    height = base_height + qr_height + extra_space_after_qr

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Fontlar (80mm uchun kattalashtirilgan)
    try:
        font_large = ImageFont.truetype("arial.ttf", 40)  # Kompaniya nomi uchun
        font_medium = ImageFont.truetype("arial.ttf", 28)  # Asosiy ma'lumotlar
        font_small = ImageFont.truetype("arial.ttf", 22)  # Kichik ma'lumotlar
        font_tiny = ImageFont.truetype("arial.ttf", 18)  # Manzil va boshqa detallar
    except Exception:
        # Default fontlar
        try:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        except Exception:
            font_large = font_medium = font_small = font_tiny = ImageFont.load_default()

    # Markazlashtirilgan matn yozish funksiyasi
    def draw_centered_text(y_pos, text, font_obj, fill_color="black"):
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        text_width = bbox[2] - bbox[0]
        x_pos = (width - text_width) // 2
        draw.text((x_pos, y_pos), text, font=font_obj, fill=fill_color)
        text_height = bbox[3] - bbox[1]
        return y_pos + text_height + 15

    # Label va qiymat yozish funksiyasi (label chapda, qiymat o'ngda)
    def draw_label_value(y_pos, label, value, font_obj, fill_color="black"):
        # Label chap tomonda
        draw.text((40, y_pos), label, font=font_obj, fill=fill_color)

        # Qiymat o'ng tomonda
        value_bbox = draw.textbbox((0, 0), value, font=font_obj)
        value_width = value_bbox[2] - value_bbox[0]
        value_x = width - value_width - 40
        draw.text((value_x, y_pos), value, font=font_obj, fill=fill_color)

        text_height = value_bbox[3] - value_bbox[1]
        return y_pos + text_height + 18

    # Header (80mm uchun kattalashtirilgan spacing)
    y = 30

    # Separator
    y = draw_centered_text(y, "=" * 48, font_small)

    # Kompaniya nomi (markazda katta fontda)
    y = draw_centered_text(y, company_name, font_large)
    y += 10

    # Kompaniya turi
    y = draw_centered_text(y, company_type, font_tiny)
    y += 15

    # Manzil (markazda)
    y = draw_centered_text(y, company_region, font_tiny)
    y = draw_centered_text(y, company_district, font_tiny)
    y = draw_centered_text(y, company_address, font_tiny)
    y += 15

    # Separator
    y = draw_centered_text(y, "=" * 48, font_small)
    y += 20

    # STIR
    y = draw_label_value(y, "STIR:", company_stir, font_medium)

    # Sana va vaqt
    date_parts = date_time.split(" ")
    if len(date_parts) == 2:
        # Sana formatini o'zgartirish (2025-11-22 -> 22/11/25)
        date_str = date_parts[0]
        try:
            from datetime import datetime as dt

            date_obj = dt.strptime(date_str, "%Y-%m-%d")
            date_formatted = date_obj.strftime("%d/%m/%y")
        except Exception:
            date_formatted = date_str
        y = draw_label_value(y, "Sana:", date_formatted, font_medium)
        y = draw_label_value(
            y, "Vaqt:", date_parts[1][:5], font_medium
        )  # Faqat soat:daqiqa
    else:
        y = draw_label_value(y, "Sana va vaqt:", date_time, font_medium)

    # Chek raqami
    receipt_display = f"№{receipt_seq.zfill(4)}" if receipt_seq else ""
    y = draw_label_value(y, "Chek raqami:", receipt_display, font_medium)

    # Separator
    y += 20
    y = draw_centered_text(y, "-" * 48, font_small)
    y += 20

    # Separator
    y = draw_centered_text(y, "=" * 48, font_small)
    y += 20

    # Fiscal ma'lumotlar
    if serial_number:
        y = draw_label_value(y, "S/N:", serial_number, font_small)

    if fm_number:
        y = draw_label_value(y, "FM raqami:", fm_number, font_small)

    if receipt_seq:
        y = draw_label_value(y, "Chek raqami:", receipt_seq, font_small)

    # Sana va vaqt (fiscal uchun)
    if len(date_parts) == 2:
        try:
            from datetime import datetime as dt

            date_obj = dt.strptime(date_parts[0], "%Y-%m-%d")
            date_formatted = date_obj.strftime("%d/%m/%y")
        except Exception:
            date_formatted = date_parts[0]
        y = draw_centered_text(y, date_formatted, font_small)
        y = draw_centered_text(y, date_parts[1][:5], font_small)

    if fiscal_sign and fiscal_sign != "None" and fiscal_sign.strip():
        y = draw_label_value(y, "Fiskal belgi:", fiscal_sign, font_small)

    if rs_version:
        y = draw_label_value(y, "RS:", rs_version, font_small)

    # Separator
    y += 20
    y = draw_centered_text(y, "=" * 48, font_small)
    y += 20

    # QR kod (80mm uchun kattalashtirilgan)
    if qr_img:
        qr_size = 320  # 80mm uchun kattalashtirilgan
        qr_img_resized = qr_img.resize((qr_size, qr_size))
        qr_x = (width - qr_size) // 2
        img.paste(qr_img_resized, (qr_x, y))
        y += qr_size

    y += 100
    y += 20
    y = draw_centered_text(y, ".", font_small)
    y += 200

    # Balandlikni to'g'rilash (QR koddan keyingi bo'shliq bilan)
    final_height = y + 100  # Qo'shimcha bo'shliq qo'shish (100px)
    if final_height != height:
        new_img = Image.new("RGB", (width, final_height), "white")
        new_img.paste(img.crop((0, 0, width, min(height, final_height))))
        img = new_img
        height = final_height

    # --- Printerga jo'natish ---
    printer_name = getattr(settings, "PRINTER_NAME", None)
    if printer_name is None:
        try:
            printer_name = win32print.GetDefaultPrinter()
        except Exception as e:
            logger.error(f"Printer topilmadi {e}")
            return False

    try:
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc("Unikassa Receipt")
            hdc.StartPage()

            # Rasmni printerga moslashtirish (80mm uchun)
            dib = ImageWin.Dib(img)
            printer_width = 576  # 80mm printer uchun (203 DPI)
            printer_height = int(height * (printer_width / width))
            dib.draw(hdc.GetHandleOutput(), (0, 0, printer_width, printer_height))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

            if entry_id:
                entry = VehicleEntry.objects.get(id=entry_id)
                entry.unikassacheck = False
                entry.save(update_fields=["unikassacheck"])

            logger.info(f"Chek muvaffaqiyatli chiqarildi: {receipt_seq}")
        finally:
            win32print.ClosePrinter(hprinter)

        # Chekni qirqish (cut) - ESC/POS komandasi (chek chiqarilgandan KEYIN)
        try:
            # Printerga to'g'ridan-to'g'ri ESC/POS cut komandasi yuborish
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                # ESC/POS cut komandasi: ESC i (0x1B 0x69)
                cut_command = b"\x1b\x69"
                win32print.StartDocPrinter(printer_handle, 1, ("Cut", None, "RAW"))
                win32print.StartPagePrinter(printer_handle)
                win32print.WritePrinter(printer_handle, cut_command)
                win32print.EndPagePrinter(printer_handle)
                win32print.EndDocPrinter(printer_handle)
                logger.info("Chek muvaffaqiyatli qirqildi")
            finally:
                win32print.ClosePrinter(printer_handle)
        except Exception as cut_error:
            logger.warning(
                f"Chekni qirqishda xatolik (bu normal bo'lishi mumkin): {str(cut_error)}"
            )

        return True
    except Exception as e:
        logger.error(f"Chek chiqarishda xatolik: {str(e)}")
        return False
