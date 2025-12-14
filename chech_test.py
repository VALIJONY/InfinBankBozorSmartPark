from smartpark.utils import print_receipt, print_simple_receipt


def main():
    print("XP-80 Printer - Chek Chiqarish")
    print("=" * 40)

    # 1. Default parametrlar bilan chek chiqarish
    print("\n1. Default chek chiqarilmoqda...")
    print_receipt()

    # 2. O'zgartirilgan parametrlar bilan chek chiqarish
    print("\n2. O'zgartirilgan chek chiqarilmoqda...")
    print_receipt(
        printer_name="XP-80",
        company_name="IDSOFT GROUP",
        project_name="SMART AUTO PARK",
        location="TOSHKENT MARKAZIY BOZORI",
        car_number="01A777BB",
        entry_time="09:30",
        exit_time="14:30",
        duration="5 soat",
        payment_amount="25000 so'm",
        thank_message="Keling yana!",
    )

    # 3. Oddiy chek chiqarish
    print("\n3. Oddiy chek chiqarilmoqda...")
    print_simple_receipt(
        printer_name="XP-80",
        title="PARKING CHEK",
        items=[
            ("Avtomobil raqami", "99B888CC"),
            ("Kirish vaqti", "08:00"),
            ("Chiqish vaqti", "18:00"),
            ("Davomiyligi", "10 soat"),
            ("To'lov summasi", "50000 so'm"),
        ],
        thank_message="Xizmat uchun rahmat!",
    )

    print("\nDastur tugadi!")


if __name__ == "__main__":
    main()
