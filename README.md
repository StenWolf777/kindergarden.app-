# Bog'chaOS — Xususiy Bog'chalar uchun B2B SaaS Tizimi

Bog'chaOS — bu xususiy maktabgacha ta'lim muassasalari boshqaruvi, jonli davomat, ota-onalar bilan Telegram orqali aloqa va to'lovlarni to'liq avtomatlashtiruvchi B2B SaaS platformasi.

---

## 📁 Loyiha Strukturasi

```
smart_bogcha/
├── run_all.bat              # Tizimni 1 bosishda to'liq ishga tushiruvchi skript
├── docs/
│   ├── PRD.md               # Mahsulot talablari hujjati (Biznes model, tariflar, rollar)
│   └── ARCHITECTURE.md      # Tizim arxitekturasi va REST API spetsifikatsiyasi
├── database/
│   └── schema.sql           # PostgreSQL 16 multi-tenant bazasi DDL va namuna ma'lumotlar
├── backend/
│   └── app/
│       ├── main.py          # FastAPI serveri (CORS, routerlar, /docs)
│       ├── database.py      # SQLite / PostgreSQL DB dvijogi va jadvallarni yaratuvchi
│       ├── telegram_bot.py  # Telegram bot notifikatsiya xizmati
│       └── routes/          # API modullari (dashboard, bolalar, davomat, moliya)
└── frontend/
    ├── index.html           # Admin Dashboard interfeysi (7 ta boshqaruv paneli)
    ├── styles.css           # Ultra-zamonaviy glassmorphic dizayn tizimi (Dark/Light)
    └── app.js               # Frontend mantiqi va API bilan real vaqtda sinxronizatsiya
```

---

## ⚡ Tezkor Ishga Tushirish

### 1-usul: Bitta bosish orqali (Tavsiya etiladi)
Loyiha papkasidagi **`run_all.bat`** faylini ikki marta bosing. Bu avtomatik ravishda:
* Backend serverni (FastAPI) `http://127.0.0.1:8000` da ishga tushiradi;
* Frontend Dashboardni `http://localhost:4321` da ishga tushiradi;
* Ikkala sahifani brauzeringizda ochadi.

### 2-usul: Terminal orqali qo'lda ishga tushirish

1. **Backend serverni yoqish:**
```bash
cd smart_bogcha/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*API hujjatlari (Swagger UI):* `http://127.0.0.1:8000/docs`

2. **Frontend veb-serverni yoqish:**
```bash
cd smart_bogcha/frontend
python -m http.server 4321
```
*Dashboard interfeysi:* `http://localhost:4321/`

---

## 🛠️ Amalga Oshirilgan Asosiy Funksiyalar

1. **Jonli Davomat:** Tarbiyachi "Keldi" tugmasini bossa, bola bazada qayd etiladi va orqa fonda ota-onasining Telegramiga chiroyli xabarnoma yuboriladi.
2. **Bolalar va Guruhlar:** Yangi bola qo'shish modal oynasi to'g'ridan-to'g'ri backend API ga ma'lumot yuboradi va bir zumda jadvalda ko'rinadi.
3. **Moliya & Kvitansiyalar:** Qarzdor oilalarga 1 tugma bilan Telegram eslatma yuborish, QR-kodli elektron to'lov kvitansiyasini chop etish (print/PDF).
4. **Oshxona & Ratsion:** Bugun kelgan bolalar soniga qarab go'sht, sut, yorma va sabzavotlar sarfini hisoblaydigan SanPin kalkulyatori.
5. **Telegram TMA (Mini App):** Ota-ona telefonida shaxsiy kabinet qanday ko'rinishini aks ettiruvchi smartfon simulyatori.
