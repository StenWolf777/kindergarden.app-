# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: teachers (tarbiyachi).** Group leaders in private kindergartens who use the system on their own smartphones, during the working day, in the classroom. Their core job is the morning attendance pass ("Keldi" / "Kelmadi" / "Sababli") for their group, plus checking on the children in it. They work with children around them, so tasks get interrupted and must be quick to resume.
- **Secondary: director, accountant/cashier, nurse/kitchen.** The director runs money, staff and reports; the accountant takes payments, chases debts and prints receipts; the nurse/kitchen handles rations and medical notes. Role-based navigation already exists (`data-roles` in `frontend/index.html`).
- **Parents** are reached through a Telegram bot and Telegram Mini App rather than this dashboard. The dashboard contains a phone simulator previewing the parent view.

## Product Purpose

Bog'chaOS is a B2B SaaS platform for private preschools and child development centres in Uzbekistan and Central Asia. It replaces paper attendance journals, Excel debt lists and chaotic Telegram group chats with one system covering children and groups, attendance, billing, staff, contracts, kitchen rations and parent communication.

Success: a teacher finishes the daily attendance pass in seconds on a phone, parents are notified automatically on Telegram, and the director sees who has paid without chasing anyone.

## Positioning

Built for how Uzbek kindergartens already operate: parents stay in Telegram (no app to install), payments go through local rails (Click, Payme, Uzum), receipts carry QR codes, kitchen supply is calculated from today's real headcount against SanPin norms, and the pricing is in UZS per kindergarten size.

## Operating Context

- Teachers use personal smartphones, often one-handed, in a busy room, on variable mobile connections.
- Attendance is marked once each morning per group; marking a child present triggers a Telegram message to the parent.
- Monthly invoices are generated on the 1st; excused absences are credited to the next month.
- The accountant reconciles cash with Click/Payme/Uzum payments and sends debt reminders over Telegram instead of SMS, to save cost.
- The kitchen plans meals (nonushta, 2-nonushta, tushlik, shirinlik, kechki ovqat) and calculates ingredients from the day's headcount.

## Capabilities and Constraints

- **Shipped panels** (`frontend/index.html`): Dashboard, Children & groups (Bolalar), Attendance (Davomat), Timesheet (Tabel), Billing (Moliya), Staff (Xodimlar), Contracts, Telegram Mini App simulator, Settings. A separate `frontend/login.html` handles sign-in.
- **Stack:** plain HTML/CSS/JS frontend served statically; FastAPI backend with SQLite locally (PostgreSQL 16 with row-level security in the target architecture); Telegram bot for notifications.
- **Roles:** super admin, director, accountant, teacher, nurse/kitchen, parent (RBAC).
- **Languages:** the interface must support **Uzbek (Latin) and Russian**. Today only Uzbek is implemented; Russian is a required addition, not yet built.
- **Device priority:** most staff use phones, so every staff-facing flow, attendance first, must work fully on a small touchscreen. Desktop is secondary.
- **Undecided:** Face ID / QR self check-in, multi-branch networks and subdomain tenancy are described in the PRD but not built.

## Brand Commitments

- Product name: **Bog'chaOS** (with the apostrophe). Page titles use "Bog'chaOS — Aqlli Bog'cha SaaS Tizimi".
- Plan names and prices from `docs/PRD.md`: Starter 450,000 UZS/month (up to 50 children), Pro 950,000 UZS/month (up to 150), Enterprise 1,900,000 UZS/month or 12,000 UZS per child.
- No logo or other brand assets are committed in the repository.

## Evidence on Hand

- `docs/PRD.md`: problems, personas, modules, pricing, legal requirements.
- `docs/ARCHITECTURE.md`: system architecture, REST API and Telegram flow.
- `database/schema.sql`: data model with sample data.
- **The product is at demo/prototype stage.** All children, groups, staff and payment figures are sample data, and there are no paying customers yet. Future work must not invent customers, testimonials, kindergarten counts, revenue or usage statistics.

## Product Principles

1. **Teacher on a phone first.** The daily attendance pass is the most frequent task; it sets the bar for speed, tap-target size and one-handed use.
2. **Telegram is the parent channel.** Parent-facing value goes through the bot and Mini App, not through new apps or SMS.
3. **Money must be unambiguous.** Amounts in UZS, debt status and payment history must be exact and readable at a glance; billing errors cost trust immediately.
4. **Children's data is protected.** Comply with Uzbekistan's personal data law and keep each kindergarten's data isolated; show staff only what their role needs.
5. **Bilingual by design.** Every label, message and receipt must work in both Uzbek and Russian, including longer Russian strings.

## Accessibility & Inclusion

- Staff range from young teachers to older employees; text must stay readable and controls large enough on small phones, in classroom light.
- Both Uzbek (Latin) and Russian must be fully supported.
