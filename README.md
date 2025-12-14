# SmartAutoPark - Avtomatik Parking Tizimi

## 📋 Loyiha haqida

SmartAutoPark - bu avtomatik parking tizimi bo'lib, avtomobillarning kirish-chiqishini boshqarish, to'lov hisoblash va real-time monitoring imkoniyatlarini taqdim etadi.

## 🚀 O'rnatish va ishga tushirish

### 🎯 Oddiy foydalanuvchilar uchun (EXE fayl)

#### 1. EXE fayl yaratish
```bash
# Build script ishga tushiring
build_exe.bat
```

#### 2. Loyihani boshqa kompyuterga ko'chirish
1. `dist/SmartPark` papkasini nusxalang
2. Maqsadli kompyuterga ko'chiring
3. `start_app.bat` faylini ishga tushiring

#### 3. Avtomatik o'rnatish
`start_app.bat` fayli avtomatik ravishda:
- PostgreSQL o'rnatadi (agar yo'q bo'lsa)
- Database yaratadi
- Migrationlarni ishga tushiradi
- Superuser yaratadi
- Loyihani ishga tushiradi

### 🔧 Rivojlantiruvchilar uchun

#### Talablar
- Python 3.8+
- PostgreSQL (ixtiyoriy - SQLite fallback mavjud)
- Redis (WebSocket uchun, ixtiyoriy)

#### 1. Loyihani klonlash
```bash
git clone <repository-url>
cd SmartAutoPark
```

#### 2. Virtual environment yaratish
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# yoki
.venv\Scripts\activate  # Windows
```

#### 3. Dependencies o'rnatish
```bash
pip install -r requirements.txt
```

#### 4. Database sozlash
```bash
# PostgreSQL bilan (tavsiya etiladi)
python setup_database.py

# yoki SQLite bilan (oddiy test uchun)
python manage.py migrate
```

#### 5. Server ishga tushirish
```bash
python manage.py runserver
```

## 🧪 Testlarni ishga tushirish

### Barcha testlarni ishga tushirish
```bash
python -m pytest -v
```

### Faqat belgilangan testlarni ishga tushirish
```bash
# Faqat calculate_amount testlari
python -m pytest smartpark/tests.py::TestVehicleEntryAmountCalculation -v

# Faqat chekka holatlar testlari
python -m pytest smartpark/tests.py::TestVehicleEntryEdgeCases -v

# Faqat model testlari
python -m pytest smartpark/tests.py::TestVehicleEntryModel -v
```

### Test coverage ko'rish
```bash
python -m pytest --cov=smartpark --cov-report=html
```

## 📊 Test natijalari

### Test statistikasi
- **Jami testlar**: 36 ta
- **Muvaffaqiyatli**: 36 ta (100%)
- **Xatoliklar**: 0 ta

### Test kategoriyalari

#### 1. Asosiy hisoblash testlari (TestVehicleEntryAmountCalculation)
- ✅ 10 daqiqa bepul vaqt
- ✅ 11 daqiqa - 1 soat hisobida
- ✅ 1 soat 1 daqiqa - 2 soat hisobida
- ✅ Aniq bir soat
- ✅ Aniq besh soat
- ✅ Limitdan oshish holatlari
- ✅ Yarim tunni kesib o'tish
- ✅ Bir necha kunlik parking

#### 2. Chekka holatlar testlari (TestVehicleEntryEdgeCases)
- ✅ Juda qisqa vaqt (30 soniya)
- ✅ Bir daqiqa
- ✅ Aniq 10 daqiqa
- ✅ Aniq 11 daqiqa
- ✅ Oyni kesib o'tish
- ✅ Yilni kesib o'tish
- ✅ Juda uzoq vaqt (10 kun)
- ✅ Bir xil vaqtda kirish-chiqish

#### 3. Model testlari (TestVehicleEntryModel)
- ✅ String ko'rinishi
- ✅ To'lov qilish

## 💰 To'lov hisoblash logikasi

### Asosiy qoidalar
1. **Bepul vaqt**: 10 daqiqa va undan kam
2. **Soat narxi**: 4000 so'm
3. **Kunlik limit**: 20000 so'm (5 soat)
4. **Yaxlitlash**: Soatni yuqoriga yaxlitlash (1 soat 1 minut = 2 soat)

### Hisoblash formulasi
```
Agar vaqt <= 10 daqiqa:
    narx = 0 so'm
Aks holda:
    soatlar = vaqt / 60
    yaxlitlangan_soatlar = int(soatlar) + (1 agar soatlar % 1 > 0 bo'lsa)
    narx = min(yaxlitlangan_soatlar * 4000, 20000)
```

### Misollar
- **5 daqiqa**: 0 so'm (bepul)
- **10 daqiqa**: 0 so'm (bepul)
- **11 daqiqa**: 4000 so'm (1 soat)
- **1 soat 1 daqiqa**: 8000 so'm (2 soat)
- **5 soat**: 20000 so'm (limit)
- **6 soat**: 20000 so'm (limit)

## 🔧 Loyiha tuzilishi

```
SmartAutoPark/
├── config/                 # Django settings
├── smartpark/             # Asosiy app
│   ├── models.py          # Database modellar
│   ├── views.py           # View funksiyalar
│   ├── consumers.py       # WebSocket consumers
│   ├── signals.py         # Django signals
│   ├── tests.py           # Test fayllar
│   └── templates/         # HTML shablonlar
├── static/                # CSS, JS, rasm fayllar
├── media/                 # Yuklangan fayllar
├── requirements.txt       # Dependencies
├── pytest.ini           # Test sozlamalari
└── README.md             # Bu fayl
```

## 🌐 API Endpoints

### Asosiy sahifalar
- `/` - Bosh sahifa
- `/home/` - Asosiy dashboard
- `/login/` - Kirish sahifasi
- `/unpaid-entries/` - To'lanmagan kirishlar

### API endpoints
- `/api/statistics/` - Statistika
- `/api/vehicle-entries/` - Avtomobil kirishlari
- `/api/mark-paid/` - To'lov qilish
- `/api/unpaid-entries/` - To'lanmagan kirishlar
- `/api/receipt/` - Chek olish

## 🔌 WebSocket

Real-time yangilanishlar uchun WebSocket ishlatiladi:
- Yangi avtomobil kirishi
- Avtomobil chiqishi
- To'lov qilish
- Statistika yangilanishi

## 🛠️ Rivojlantirish

### Yangi test qo'shish
```python
def test_yangi_holat(self):
    """Yangi test holati"""
    # Vaqt: 2025-08-30 08:00 -> 2025-08-30 10:00 (2 soat)
    # Hisoblash: 120 daqiqa > 10 daqiqa, 120/60 = 2.0 soat -> 2 soat = 8000 so'm
    entry = VehicleEntry(
        number_plate="10A777AA",
        entry_time=make_aware(datetime(2025, 8, 30, 8)),
        exit_time=make_aware(datetime(2025, 8, 30, 10)),
    )
    assert entry.calculate_amount() == 8000
```

### Test comment format
Har bir test uchun quyidagi formatda comment yozing:
```python
# Vaqt: [kirish vaqti] -> [chiqish vaqti] ([davomiyligi])
# Hisoblash: [batafsil hisoblash jarayoni] = [natija] so'm
```

## 📝 Eslatmalar

- Testlar database yaratmasdan ishlaydi
- Har bir test o'z-o'zini tozalaydi
- Test coverage 100% ga yaqin
- Barcha chekka holatlar qamrab olingan

## 🤝 Hissa qo'shish

1. Fork qiling
2. Feature branch yarating
3. O'zgarishlarni commit qiling
4. Testlarni ishga tushiring
5. Pull request yuboring

## 📞 Aloqa

Muammolar yoki savollar uchun issue oching yoki email yuboring.

---

**Loyiha**: SmartAutoPark  
**Versiya**: 1.0.0  
**Yaratilgan**: 2025  
**Litsenziya**: MIT



