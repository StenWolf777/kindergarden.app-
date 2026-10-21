# Bog'chaOS — Xususiy Bog'chalar uchun B2B SaaS Tizimi
## Mahsulot Talablari Hujjati (PRD - Product Requirement Document)

---

### 1. Kirish va Mahsulot Maqsadi
**Bog'chaOS** — bu O'zbekiston va Markaziy Osiyo bozoridagi xususiy maktabgacha ta'lim muassasalari (bog'chalar), o'quv-rivojlantirish markazlari uchun barcha ma'muriy, moliyaviy va ota-onalar bilan aloqa jarayonlarini to'liq avtomatlashtiruvchi B2B SaaS platformasi.

#### Asosiy Muammolar (Pain Points):
1. **Moliyaviy tartibsizlik va kechiktirilgan to'lovlar:** Ota-onalar to'lovlarni o'z vaqtida qilmaydi, qarzdorliklar daftarda yoki Excelda yo'qolib ketadi.
2. **Davomat va xavfsizlik nazorati sustligi:** Bola kelgan-kelmaganini ota-ona bilmaydi, tarbiyachilar qog'oz jurnal to'ldirishga ko'p vaqt sarflaydi.
3. **Oziq-ovqat va oshxona isrofgarchiligi:** Kunlik kelgan bolalar soniga qarab masalliq sarfini hisoblash qiyin, o'g'irlik va ortiqcha xarajatlar yuzaga keladi.
4. **Ota-onalar bilan zaif aloqa:** Telegram guruhlaridagi tartibsizlik (savollar, cheklar, shikoyatlar bir joyga aralashib ketadi).

---

### 2. Maqsadli Auditoriya va Foydalanuvchi Rollari (Personas)

| Rol | Kim | Asosiy vazifasi |
| :--- | :--- | :--- |
| **Super Admin** | Platforma egasi (Siz) | Bog'chalar obunalarini boshqarish, global statistika, tariflar, billing. |
| **Bog'cha Direktori** | Bog'cha egasi / Menejer | Moliyaviy oqimlar, xodimlar nazorati, filiallar, hisobotlar va tushumlar. |
| **Buxgalter / Kassir** | Moliya xodimi | To'lovlarni qabul qilish, kvitansiyalar, Click/Payme to'lovlarini solishtirish. |
| **Tarbiyachi** | Guruh rahbari | Kunlik davomat, bolalar kayfiyati, darslar, mashg'ulot rasmlari, menyu. |
| **Oshxona / Hamshira** | Tibbiy va ta'minot xodimi | Kunlik ratsion, allergenlar, bolalarning tibbiy kartasi, masalliq normasi. |
| **Ota-ona** | Bolaning ota-onasi | Farzandi davomati, kunlik holati, to'lovlar, to'lov tarixi, bog'cha yangiliklari. |

---

### 3. Asosiy Funksional Modullar (Core Modules)

#### 3.1. Tashkilot va Filiallar (Multi-Tenancy)
* Har bir bog'cha mustaqil subdomen yoki unikal ID orqali tizimga ulanadi (`bogcha1.bogchaos.uz`).
* Bir nechta filialga ega bo'lgan bog'chalar tarmoq sifatida birlashtiriladi.
* Rollarga asoslangan ruxsatlar tizimi (RBAC - Role Based Access Control).

#### 3.2. Bolalar va Guruhlar Boshqaruvi
* Bolaning to'liq profili: F.I.Sh., tug'ilgan sanasi, manzili, ota-onasining kontaktlari, tibbiy xususiyatlari (allergiyalar).
* Guruhlar: Yosh toifasiga ko'ra (Kichik guruh, O'rta guruh, Katta guruh, Tayyorlov guruhi).
* Guruh sig'imi va bo'sh o'rinlar monitoringi.

#### 3.3. Aqlli Davomat Tizimi
* **Tarbiyachi rejimi:** Har kuni ertalab 1 tugma bilan "Keldi", "Kelmadi", "Sababli" belgilash.
* **Avtomatik notifikatsiya:** Bola belgilaniboq ota-onaning Telegramiga avtomatik xabarnoma boradi: *"Farzandingiz Alisher soat 08:30 da bog'chaga yetib keldi."*
* **Integratsiya imkoniyati:** Planshet Face ID yoki QR-kod orqali avtomatik qayd etish.

#### 3.4. Moliya, Hisob-kitob va Billing
* Oylik abonent to'lovi hisobi (har oyning 1-sanasida avtomatik hisob shakllantiriladi).
* Kelmagan kunlar hisobi (agar sababli bo'lsa, keyingi oydan chegirib tashlash formulasi).
* Click, Payme, Uzum to'lov tizimlari orqali to'lov havolasi generatsiyasi.
* QR-kodli elektron kvitansiyalar va cheklar.
* Ota-onaga qarzdorlik haqida avtomatik Telegram-eslatmalar (SMS xarajatini tejash uchun).

#### 3.5. Taomnoma va Oshxona Hisob-kitobi (Smart Kitchen)
* Haftalik va oylik tasdiqlangan taomnoma (Nonushta, 2-nonushta, Tushlik, Shirinlik, Kechki ovqat).
* Bugungi kelgan bolalar soni bo'yicha masalliq kalkulyatori:
  * Masalan: 40 ta bola keldi -> Go'sht: 4 kg, Kartoshka: 6 kg, Non: 8 ta.
* Ota-onalar farzandi bugun nima yeyishini ilovada ko'rib turadi.

#### 3.6. Ota-onalar uchun Telegram Web App (TMA)
* Ota-ona yangi mobil ilova yuklab o'tirmaydi.
* Telegram botga kirib `/start` bosadi va telefon raqami orqali shaxsiy kabinet ochiladi.
* Imkoniyatlar:
  * Farzandining bugungi davomati va oylik kalendari;
  * Oylik hisob-kitob va 1 klikda Payme/Click orqali to'lash;
  * Kunlik taomnoma va tarbiyachi yuklagan rasmlar galereyasi;
  * Tarbiyachiga xabar qoldirish (masalan: *"Bugun kechroq olib ketamiz"*).

---

### 4. Biznes Model va Tariflar (Monetization Strategy)

1. **Starter Plan (Kichik bog'chalar - 50 tagacha bola):**
   * Narxi: 450,000 UZS / oy
   * Imkoniyatlar: Bolalar bazasi, Davomat, Oylik to'lovlar, Telegram bot.
2. **Pro Plan (O'rta bog'chalar - 150 tagacha bola):**
   * Narxi: 950,000 UZS / oy
   * Imkoniyatlar: Starter + Oshxona taomnomasi, Kvitansiyalar, Ota-onalar galereyasi, Ko'p xodimlik rejim.
3. **Enterprise / Tarmoq Plan (Cheksiz bolalar + bir nechta filial):**
   * Narxi: 1,900,000 UZS / oy (yoki har bir bola uchun 12,000 UZS)
   * Imkoniyatlar: Pro + Face ID integratsiyasi, Alohida brending, Maxsus hisobotlar, Prioritet texnik yordam.

---

### 5. Xavfsizlik, Ma'lumotlar Himoyasi va Qonuniylik
* Bolalar shaxsiy ma'lumotlarini himoyalash (O'zbekiston Respublikasining "Shaxsga doir ma'lumotlar to'g'risida"gi Qonuni talablariga moslik).
* Har bir bog'cha ma'lumoti PostgreSQL Row-Level Security (RLS) orqali to'liq izolyatsiya qilinadi.
* Kunlik avtomatik zaxira nusxalari (Backups).
