import serial
import time
import os


def control_barrier_time(delay_seconds=10):
    """
    Shlakboumni ochadi va N soniyadan keyin avtomatik yopadi.
    """
    try:
        # Operating system ga qarab port nomini aniqlash
        if os.name == "nt":  # Windows
            port = "COM3"  # Windows da COM3, COM4, COM5... bo'lishi mumkin
        else:  # Linux/Mac
            port = "/dev/ttyUSB0"  # Linux da /dev/ttyUSB0, /dev/ttyUSB1...

        baudrate = 9600

        with serial.Serial(port, baudrate, timeout=1) as ser:
            time.sleep(2)  # Port ochilgandan keyin barqarorlashish

            # Ochish buyrug'i
            ser.write(
                b"O"
            )  # Bu sizning qurilmangizga bog'liq (masalan b'\xA0\x01\x01\xA2')
            print("✅ Barrier OPEN command sent")

            # Kutish
            time.sleep(delay_seconds)

            # Yopish buyrug'i
            ser.write(b"C")
            print("✅ Barrier CLOSE command sent")

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def control_barrier_command(action="open"):
    """
    Shlakbaumni boshqarish: 'open' yoki 'close'
    Qurilmaga serial orqali signal yuboradi.
    """
    try:
        # Operating system ga qarab port nomini aniqlash
        if os.name == "nt":  # Windows
            port = "COM3"  # Windows da COM3, COM4, COM5... bo'lishi mumkin
        else:  # Linux/Mac
            port = "/dev/ttyUSB0"  # Linux da /dev/ttyUSB0, /dev/ttyUSB1...

        baudrate = 9600  # Modulga mos ravishda sozlang (odatda 9600)

        # Command ni aniqlash
        if action == "open":
            command = b"O"  # O = Open (sizning modulga bog'liq, ba'zida b'\xA0\x01\x01\xA2' bo'lishi mumkin)
        elif action == "close":
            command = b"C"  # C = Close
        else:
            raise ValueError("Action must be 'open' or 'close'")

        # Serial port ochiladi
        with serial.Serial(port, baudrate, timeout=1) as ser:
            time.sleep(2)  # Port ochilgandan keyin kutish
            ser.write(command)
            print(f"✅ Barrier command sent: {action}")

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
        # Windows da COM port topilmagan bo'lsa, boshqa COM portlarni sinab ko'rish
        if os.name == "nt":
            print("🔄 Trying other COM ports...")
            for com_port in ["COM1", "COM2", "COM4", "COM5", "COM6", "COM7", "COM8"]:
                try:
                    with serial.Serial(com_port, baudrate, timeout=1) as ser:
                        time.sleep(1)
                        ser.write(command)
                        print(f"✅ Barrier command sent via {com_port}: {action}")
                        return
                except Exception:
                    continue
            print("❌ No available COM ports found")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
