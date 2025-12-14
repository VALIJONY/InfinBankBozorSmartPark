# 🚀 SmartPark - Tezkor Boshlash Qo'llanmasi

## 📦 EXE fayl yaratish va tarqatish

### 1. EXE fayl yaratish
```bash
# Build script ishga tushiring
build_exe.bat
```

Bu script:
- Virtual environment yaratadi
- Barcha dependencies o'rnatadi
- PyInstaller bilan exe fayl yaratadi
- Kerakli fayllarni nusxalaydi

### 2. Natija
`dist/SmartPark/` papkasida quyidagi fayllar yaratiladi:
- `SmartPark.exe` - Asosiy dastur
- `start_app.bat` - Loyihani ishga tushirish
- `install_postgres.bat` - PostgreSQL o'rnatish
- `install_redis.bat` - Redis o'rnatish
- `setup_database.py` - Database sozlash
- `README.md` - Qo'llanma

## 🖥️ Boshqa kompyuterga o'tkazish

### 1. Fayllarni nusxalash
`dist/SmartPark/` papkasini butunlay nusxalang va boshqa kompyuterga ko'chiring.

### 2. Loyihani ishga tushirish
Maqsadli kompyuterga:
1. `SmartPark` papkasini oching
2. `start_app.bat` faylini ishga tushiring
3. Avtomatik o'rnatish jarayonini kuting

### 3. Avtomatik o'rnatish jarayoni
`start_app.bat` quyidagi ishlarni avtomatik bajaradi:
- PostgreSQL o'rnatadi (agar yo'q bo'lsa)
- Redis o'rnatadi (agar yo'q bo'lsa)
- Database yaratadi
- Migrationlarni ishga tushiradi
- Superuser yaratadi (admin/admin123)
- Loyihani ishga tushiradi

## 🌐 Loyihani ishlatish

### Kirish ma'lumotlari
- **URL**: http://localhost:8000
- **Admin panel**: http://localhost:8000/admin
- **Username**: admin
- **Password**: admin123

### Asosiy funksiyalar
- Avtomobil kirish/chiqish
- To'lov hisoblash
- Real-time monitoring
- Statistika ko'rish
- Chek chiqarish

## ⚠️ Muhim eslatmalar

### Tizim talablari
- Windows 10/11
- Internet ulanishi (birinchi marta o'rnatish uchun)
- Administrator huquqlari (PostgreSQL/Redis o'rnatish uchun)

### Xavfsizlik
- Birinchi marta ishga tushirgandan keyin admin parolini o'zgartiring
- Production muhitida SECRET_KEY ni o'zgartiring

### Muammolar
Agar muammo bo'lsa:
1. `install_postgres.bat` ni alohida ishga tushiring
2. `install_redis.bat` ni alohida ishga tushiring
3. `setup_database.py` ni alohida ishga tushiring

## 📞 Yordam

Muammolar uchun:
- README.md faylini o'qing
- Log fayllarni tekshiring
- GitHub issues oching

---

**Loyiha**: SmartPark  
**Versiya**: 1.0.0  
**Platforma**: Windows  
**Dasturlash tili**: Python/Django
