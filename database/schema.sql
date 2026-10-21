-- ============================================================================
-- Bog'chaOS: PostgreSQL Multi-Tenant Database Schema
-- Versiya: 1.0.0
-- Maqsad: Bog'chalar boshqaruvi, davomat, to'lovlar va ota-onalar portali
-- ============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enums
CREATE TYPE user_role_enum AS ENUM (
    'SUPER_ADMIN', 
    'DIRECTOR', 
    'ACCOUNTANT', 
    'TEACHER', 
    'NURSE', 
    'PARENT'
);

CREATE TYPE attendance_status_enum AS ENUM (
    'PRESENT', 
    'ABSENT', 
    'EXCUSED'
);

CREATE TYPE invoice_status_enum AS ENUM (
    'DRAFT', 
    'UNPAID', 
    'PARTIALLY_PAID', 
    'PAID', 
    'OVERDUE', 
    'CANCELLED'
);

CREATE TYPE payment_method_enum AS ENUM (
    'CASH', 
    'CLICK', 
    'PAYME', 
    'UZUM', 
    'BANK_TRANSFER'
);

CREATE TYPE plan_tier_enum AS ENUM (
    'STARTER', 
    'PRO', 
    'ENTERPRISE'
);

-- 1. Tashkilotlar (Bog'chalar - Tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email VARCHAR(100),
    address TEXT,
    logo_url TEXT,
    plan_tier plan_tier_enum DEFAULT 'STARTER',
    subscription_expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Filiallar (Branches)
CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    phone VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_branches_org_id ON branches(org_id);

-- 3. Foydalanuvchilar (Users)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role user_role_enum NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telegram_chat_id BIGINT,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_telegram_chat_id ON users(telegram_chat_id);

-- 4. Guruhlar (Groups)
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    age_category VARCHAR(50) NOT NULL, -- Masalan: '3-4 yosh (Kichik guruh)'
    capacity INT DEFAULT 25,
    primary_teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    assistant_teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
    monthly_fee NUMERIC(12, 2) NOT NULL DEFAULT 1500000.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_groups_org_id ON groups(org_id);

-- 5. Bolalar (Children)
CREATE TABLE children (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE RESTRICT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('MALE', 'FEMALE')),
    photo_url TEXT,
    allergies TEXT,
    medical_notes TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'GRADUATED', 'PAUSED')),
    enrolled_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_children_org_id ON children(org_id);
CREATE INDEX idx_children_group_id ON children(group_id);

-- 6. Ota-onalar (Parents)
CREATE TABLE parents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    relationship VARCHAR(30) NOT NULL, -- 'OTA', 'ONA', 'VASIY'
    telegram_chat_id BIGINT,
    workplace VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_parents_org_id ON parents(org_id);
CREATE INDEX idx_parents_phone ON parents(phone);

-- 7. Bolalar va Ota-onalar bog'lanishi (Child <-> Parent M2M)
CREATE TABLE child_parents (
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    parent_id UUID NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
    is_primary_contact BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (child_id, parent_id)
);

-- 8. Davomat (Attendance)
CREATE TABLE attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status attendance_status_enum NOT NULL DEFAULT 'PRESENT',
    check_in_time TIME,
    check_out_time TIME,
    marked_by_user_id UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_child_daily_attendance UNIQUE (child_id, date)
);
CREATE INDEX idx_attendance_org_date ON attendance(org_id, date);
CREATE INDEX idx_attendance_group_date ON attendance(group_id, date);

-- 9. Hisob-fakturalar / Oylik to'lovlar (Billing Invoices)
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL,
    billing_period VARCHAR(7) NOT NULL, -- '2026-10'
    base_amount NUMERIC(12, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) DEFAULT 0.00,
    compensation_amount NUMERIC(12, 2) DEFAULT 0.00, -- O'tgan oydagi sababli kelmagan kunlar kompensatsiyasi
    total_due NUMERIC(12, 2) NOT NULL,
    amount_paid NUMERIC(12, 2) DEFAULT 0.00,
    status invoice_status_enum DEFAULT 'UNPAID',
    due_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_child_billing_period UNIQUE (child_id, billing_period)
);
CREATE INDEX idx_invoices_org_status ON invoices(org_id, status);

-- 10. To'lovlar (Payments)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL,
    payment_method payment_method_enum NOT NULL,
    external_transaction_id VARCHAR(100),
    payer_name VARCHAR(150),
    notes TEXT,
    received_by_user_id UUID REFERENCES users(id),
    paid_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_payments_org_id ON payments(org_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);

-- 11. Taomnoma va Oshxona Menyusi (Meal Menus)
CREATE TABLE meal_menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    meal_type VARCHAR(50) NOT NULL, -- 'NONUSHTA', 'TUSHLIK', 'IKKINCHI_TUSHLIK', 'KECHKI_OVQAT'
    dish_name VARCHAR(200) NOT NULL,
    description TEXT,
    calories INT,
    allergens VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_meal_menus_org_date ON meal_menus(org_id, date);

-- 12. Telegram va Notifikatsiyalar Jurnali
CREATE TABLE notifications_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    recipient_type VARCHAR(20) NOT NULL, -- 'PARENT', 'TEACHER'
    recipient_id UUID,
    telegram_chat_id BIGINT,
    phone VARCHAR(30),
    notification_type VARCHAR(50) NOT NULL, -- 'ATTENDANCE_IN', 'INVOICE_DUE', 'PAYMENT_RECEIPT'
    payload TEXT NOT NULL,
    is_delivered BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- DEMO SEED DATA (Namuna ma'lumotlar)
-- ============================================================================

INSERT INTO organizations (id, name, slug, phone, email, address, plan_tier) VALUES
('a0000000-0000-0000-0000-000000000001', 'Smart Kids Academy', 'smart-kids', '+998712001122', 'info@smartkids.uz', 'Toshkent sh., Chilonzor tumani, 5-mavze', 'PRO');

INSERT INTO branches (id, org_id, name, address, phone) VALUES
('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Chilonzor Filiali', 'Chilonzor 5-mavze, 12-uy', '+998901234567');

INSERT INTO users (id, org_id, role, full_name, phone, password_hash) VALUES
('u0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'DIRECTOR', 'Nodira Azimova', '+998901112233', '$2a$12$demo_hash_directora'),
('u0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'TEACHER', 'Gulbahor Karimova', '+998934445566', '$2a$12$demo_hash_teachera');

INSERT INTO groups (id, org_id, branch_id, name, age_category, capacity, primary_teacher_id, monthly_fee) VALUES
('g0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Yulduzcha (Kichik guruh)', '3-4 yosh', 20, 'u0000000-0000-0000-0000-000000000002', 1800000.00),
('g0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Qaldirg''och (Tayyorlov guruhi)', '5-6 yosh', 25, 'u0000000-0000-0000-0000-000000000002', 2000000.00);

INSERT INTO children (id, org_id, branch_id, group_id, first_name, last_name, birth_date, gender, allergies) VALUES
('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'g0000000-0000-0000-0000-000000000001', 'Imron', 'Rahimov', '2022-04-15', 'MALE', 'Tuxum oqiga allergiya'),
('c0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'g0000000-0000-0000-0000-000000000001', 'Madina', 'Saidova', '2022-06-20', 'FEMALE', 'Yo''q'),
('c0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'g0000000-0000-0000-0000-000000000001', 'Jasur', 'Aliyev', '2022-01-10', 'MALE', 'Laktaza yetishmovchiligi');
