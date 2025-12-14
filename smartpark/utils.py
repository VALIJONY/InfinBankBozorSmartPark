import sys
from django.conf import settings
from datetime import datetime

if sys.platform.startswith("win"):
    import win32print  # type: ignore[import]
else:
    win32print = None  # type: ignore[assignment]


def _resolve_printer_name(preferred_name: str | None) -> str:
    """Pick a valid Windows printer name.

    Order of precedence:
    1) Explicit preferred_name if exists
    2) settings.PRINTER_NAME if exists
    3) Partial match (contains) against installed printers
    4) System default printer
    Raises ValueError if nothing suitable found.
    """
    if win32print is None:
        raise ValueError(
            "Printing is only supported on Windows (win32print not available)."
        )

    # List installed printers (name only)
    installed = [
        p[2]
        for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
    ]

    candidates = []
    if preferred_name:
        candidates.append(preferred_name)
    env_name = getattr(settings, "PRINTER_NAME", None)
    if env_name and env_name not in candidates:
        candidates.append(env_name)

    # 1-2) exact match
    for name in candidates:
        if name and name in installed:
            return name

    # 3) partial contains match (case-insensitive)
    lowers = [n.lower() for n in installed]
    for cand in candidates:
        if cand:
            cand_l = cand.lower()
            for i, n_l in enumerate(lowers):
                if cand_l in n_l:
                    return installed[i]

    # 4) default printer
    try:
        default_name = win32print.GetDefaultPrinter()
        if default_name:
            return default_name
    except Exception:
        pass

    raise ValueError(
        "No suitable printer found. Set PRINTER_NAME or install a printer."
    )


def print_receipt(
    printer_name=None,
    company_name="IDSOFT GROUP",
    project_name="SMART AUTO PARK",
    location="URGANCH MARKAZIY DEHQON BOZORI",
    address="7-SHAX JIZZAX KO'CHA 1-UY",
    car_number=None,
    entry_time=None,
    exit_time=None,
    duration=None,
    payment_amount=None,
    thank_message="Tashrifingiz uchun Rahmat!",
):
    """
    Print receipt to thermal printer with customizable parameters

    Args:
        printer_name (str): Printer name (default: "XP-80")
        company_name (str): Company name (default: "IDSOFT GROUP")
        project_name (str): Project name (default: "SMART AUTO PARK")
        location (str): Location address (default: "URGANCH MARKAZIY DEHQON BOZORI")
        car_number (str): Car plate number (default: "90A900BA")
        entry_time (str): Entry time (default: "10:00")
        exit_time (str): Exit time (default: "12:00")
        duration (str): Duration (default: "2 soat")
        payment_amount (str): Payment amount (default: "12000 so'm")
        thank_message (str): Thank you message (default: "Rahmat!")

    Returns:
        bool: True if successful, False otherwise
    """

    # ESC/POS commands
    INIT = b"\x1b\x40"  # Printer reset
    CENTER = b"\x1b\x61\x01"  # Center alignment
    LEFT = b"\x1b\x61\x00"  # Left alignment
    DOUBLE_HEIGHT = b"\x1b\x21\x10"  # Double height font
    NORMAL = b"\x1b\x21\x00"  # Normal font
    CUT = b"\x1d\x56\x00"  # Paper cut

    # Build receipt data
    data = b""
    data += INIT
    data += DOUBLE_HEIGHT

    data += CENTER + location.encode("utf-8") + b"\n"
    data += CENTER + address.encode("utf-8") + b"\n"
    data += CENTER + b"\n"

    data += b"========================================\n"
    data += LEFT + b"Avtomobil raqami : " + car_number.encode("utf-8") + b"\n"
    data += LEFT + b"Kirish vaqti     : " + entry_time.encode("utf-8") + b"\n"
    data += LEFT + b"Chiqish vaqti    : " + exit_time.encode("utf-8") + b"\n"
    data += LEFT + b"Davomiyligi      : " + duration.encode("utf-8") + b"\n"
    data += LEFT + b"To'lov summasi   : " + payment_amount.encode("utf-8") + b"\n"
    data += b"========================================\n"
    data += CENTER + thank_message.encode("utf-8") + b"\n\n\n\n\n\n"
    data += NORMAL
    data += CUT

    if win32print is None:
        # Linux yoki boshqa non-Windows platformalarda faqat log, printerga yubormaymiz
        print(
            "[INFO] print_receipt: win32print mavjud emas (non-Windows). Chek konsolga chiqarildi:"
        )
        print(data)
        return True

    try:
        # Resolve printer name robustly
        resolved_printer = _resolve_printer_name(printer_name)
        # Send to printer
        hprinter = win32print.OpenPrinter(resolved_printer)
        win32print.StartDocPrinter(hprinter, 1, ("Chek", None, "RAW"))
        win32print.StartPagePrinter(hprinter)
        win32print.WritePrinter(hprinter, data)
        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)
        win32print.ClosePrinter(hprinter)

        print(
            f"[OK] Chiroyli chek '{resolved_printer}' printeriga chiqarildi va qirqildi!"
        )
        return True

    except Exception as e:
        print(f"[ERROR] Xatolik yuz berdi: {e}")
        return False


def print_stats_receipt(
    *,
    printer_name=None,
    title="Batafsil statistika",
    date_from: str | None = None,
    date_to: str | None = None,
    filters: dict | None = None,
    paid_count: int = 0,
    paid_sum: int | float = 0,
    unpaid_zero_count: int = 0,
    inside_count: int = 0,
    exited_count: int = 0,
    footer_message: str = "Rahmat!",
):
    """Print only summary statistics to a thermal printer using ESC/POS.

    Returns:
        tuple[bool, str | None]: (success, error_message)
    """
    # ESC/POS commands
    INIT = b"\x1b\x40"  # Initialize
    CENTER = b"\x1b\x61\x01"  # Align center
    LEFT = b"\x1b\x61\x00"  # Align left
    NORMAL = b"\x1b\x21\x00"  # Normal font
    BOLD_ON = b"\x1b\x45\x01"  # Emphasis on
    BOLD_OFF = b"\x1b\x45\x00"  # Emphasis off
    CUT = b"\x1d\x56\x00"  # Cut

    def line(text: str = "") -> bytes:
        return (text or "").encode("utf-8") + b"\n"

    def sep(char: str = "=") -> bytes:
        return line((char * 32))

    def row(label: str, value: str) -> bytes:
        # 32-char width formatting, left label / right value
        label = label or ""
        value = value or ""
        # Truncate if too long
        label_trimmed = label[:20]
        value_trimmed = value[:12]
        pad = max(0, 32 - len(label_trimmed) - len(value_trimmed))
        return line(f"{label_trimmed}{' ' * pad}{value_trimmed}")

    data = b""
    data += INIT
    # Header (project name removed as requested)
    data += NORMAL + CENTER + BOLD_ON + line(title) + BOLD_OFF
    data += CENTER + sep("=")

    # Date range
    if date_from or date_to:
        # Use ASCII hyphen to avoid unsupported glyphs on some ESC/POS printers
        data += LEFT + line(f"Sana: {date_from or '-'} - {date_to or '-'}")
    # Printed time with date
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    data += LEFT + line(f"Chop etilgan vaqt: {now_str}")

    # Filters hidden by request: do not print extra filter lines, keep receipt concise.

    data += LEFT + sep("-")
    data += LEFT + row("To'langan", f"{paid_count} ta")
    try:
        paid_sum_int = int(paid_sum)
    except Exception:
        paid_sum_int = 0
    # Emphasize total
    data += (
        LEFT
        + BOLD_ON
        + row("Jami tushum", f"{paid_sum_int:,} so'm".replace(",", " "))
        + BOLD_OFF
    )
    data += LEFT + row("0 so'm (to'langan)", f"{unpaid_zero_count} ta")
    data += LEFT + row("Ichkarida", f"{inside_count} ta")
    data += LEFT + row("Chiqib ketgan", f"{exited_count} ta")
    data += CENTER + sep("=")
    data += CENTER + line(footer_message)
    # Feed a few lines so footer is above the cut on the same receipt
    data += b"\n\n\n\n"
    data += CUT

    if win32print is None:
        # Non-Windows: printer yo'q, faqat data ni log qilamiz
        print(
            "[INFO] print_stats_receipt: win32print mavjud emas (non-Windows). Statistika cheki konsolga chiqarildi:"
        )
        print(data)
        return True, None

    try:
        resolved_printer = _resolve_printer_name(printer_name)
        h = win32print.OpenPrinter(resolved_printer)
        win32print.StartDocPrinter(h, 1, ("Statistika", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, data)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
        win32print.ClosePrinter(h)
        print(f"[OK] Statistika cheki '{resolved_printer}' ga yuborildi")
        return True, None
    except Exception as e:
        err = str(e)
        print(f"[ERROR] Chek chiqarishda xatolik: {err}")
        return False, err
