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

## 🔐 Xavfsizlik va Rollar

* Har bir API so'rovi imzolangan, 12 soatda tugaydigan token bilan tekshiriladi; token bo'lmasa server ma'lumot bermaydi.
* Rollar va ruxsatlar bitta jadvalda: `backend/app/security.py` dagi `PERMISSIONS`. Sahifa ham shu ro'yxatni `/api/v1/auth/me` orqali oladi.
* Parollar PBKDF2 xeshi ko'rinishida saqlanadi. Eski ochiq parollar birinchi ishga tushishda avtomatik xeshlanadi.
* Har bir bog'cha faqat o'z ma'lumotini ko'radi (`org_id` tokendan olinadi).

| Rol | Ko'radigan bo'limlar | Asosiy cheklovlar |
| :--- | :--- | :--- |
| Direktor / Super Admin | Hammasi | — |
| Buxgalter | Asosiy panel, Bolalar, Davomat (faqat ko'rish), Tabel, Moliya, Xodimlar | Guruh ochmaydi, bola o'chirmaydi, davomat belgilamaydi |
| Tarbiyachi | Bolalar, Davomat | Pul ma'lumotlarini ko'rmaydi, bola qo'shmaydi/o'chirmaydi |
| Hamshira | Bolalar, Davomat (faqat ko'rish) | Faqat sog'liq ma'lumotini tahrirlaydi |

**Muhit o'zgaruvchilari (real serverda):**
* `BOGCHA_SECRET_KEY` — token imzolash kaliti. Berilmasa, `backend/.secret_key` fayli avtomatik yaratiladi (gitga qo'shilmaydi).
* `BOGCHA_ALLOWED_ORIGINS` — API ga murojaat qila oladigan saytlar, vergul bilan (standart: `http://localhost:4321,http://127.0.0.1:4321`).
* Tizimga faqat telefon raqam va parol bilan kiriladi.

---

## 📲 Telegram bot (ota-onalarga davomat xabari)

* Bot tokeni `backend/.env` faylida saqlanadi: `TELEGRAM_BOT_TOKEN=...` (bu fayl gitga qo'shilmaydi).
* Server ishga tushganda bot avtomatik ulanadi va ota-onalarning xabarlarini tinglaydi.
* **Ota-onani ulash:** *Bolalar & Guruhlar* bo'limida bola qatoridagi **Telegram** tugmasini bosing, shaxsiy havolani nusxalab ota-onaga yuboring. Ota-ona havolani ochib **Start** bosadi va ulanadi.
* Muqobil usul: ota-ona botga `/start` yozib, telefon raqamini yuboradi. Bu faqat bolaning kartasida ota-ona telefoni to'g'ri yozilgan bo'lsa ishlaydi.
* Davomat belgilanganda (Keldi, Kelmadi, Sababli, Kech keldi) faqat ulangan ota-onalarga xabar boradi. Telegram telefon raqamiga to'g'ridan-to'g'ri xabar yubora olmaydi.
* **Rasm yuborish:** direktor *Rasm yuborish* bo'limida kanal manzilini kiritib ulaydi (bot kanalda administrator bo'lishi kerak). Shundan so'ng tarbiyachi yoki direktor 10 tagacha rasmni kanalga yoki bitta bolaning ota-onasiga yuboradi. Rasmlar brauzerda kichraytiriladi (1600 px).
* Bolalar rasmlari shaxsiy ma'lumot: kanalni yopiq (private) qiling va ota-onalarning roziligini oling.

---

## 📊 Moliya va boshqaruv funksiyalari

* **Bajarish kerak** (Asosiy panel): belgilanmagan davomat (guruh bo'yicha), muddati o'tgan to'lovlar, belgilanmagan xodimlar, sig'imdan oshgan guruhlar, Telegramga ulanmagan ota-onalar. Har biri tegishli bo'limni ochadi.
* **Oy bo'yicha yig'im va eng katta qarzdorlar:** oy rejasining necha foizi yig'ilgani, qoldiq va muddati o'tgan hisoblar.
* **To'lov oynasi:** qarz holati, oy tanlash (oldindan to'lov uchun shu oy hisobi ochiladi), 6 ta usul (Naqd, Click, Payme, Karta, O'tkazma, Ilova), izoh. Usul tanlanmaguncha saqlanmaydi.
* **Avtomatik to'lov eslatmalari** (Moliya): muddatdan N kun oldin va keyin, kuniga 6 martagacha, `{childName}`, `{parentName}`, `{amount}`, `{dueDate}`, `{group}` maydonli matn. Faqat Telegramga ulangan ota-onalarga yuboriladi.
* **Xodimlar davomati** (Xodimlar & Maosh): Keldi / Kelmadi / Sababli / Kech keldi; asosiy panelda "bugun ishda" ko'rinadi.
* **Guruh holati:** to'lish halqasi, sig'imdan oshsa ogohlantirish, 2 tagacha tarbiyachi, guruhni tahrirlash.

---

## 🛠️ Amalga Oshirilgan Asosiy Funksiyalar

1. **Jonli Davomat:** Tarbiyachi "Keldi" tugmasini bossa, bola bazada qayd etiladi va orqa fonda ota-onasining Telegramiga chiroyli xabarnoma yuboriladi.
2. **Bolalar va Guruhlar:** Yangi bola qo'shish modal oynasi to'g'ridan-to'g'ri backend API ga ma'lumot yuboradi va bir zumda jadvalda ko'rinadi.
3. **Moliya & Kvitansiyalar:** Qarzdor oilalarga 1 tugma bilan Telegram eslatma yuborish, QR-kodli elektron to'lov kvitansiyasini chop etish (print/PDF).
4. **Oshxona & Ratsion:** Bugun kelgan bolalar soniga qarab go'sht, sut, yorma va sabzavotlar sarfini hisoblaydigan SanPin kalkulyatori.
5. **Telegram TMA (Mini App):** Ota-ona telefonida shaxsiy kabinet qanday ko'rinishini aks ettiruvchi smartfon simulyatori.
