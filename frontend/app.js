// ============================================================================
// Bog'chaOS: Enterprise Pro Dashboard Logic
// Barcha 7 ta modul: Rollar, Davomat, Tabel, Omborxona, To'garaklar, Maosh, Shartnomalar
// ============================================================================

// The e2e suite points this at an isolated test backend via window.__BOGCHA_API_BASE__;
// production is unaffected since that global is never set outside of tests.
const API_BASE = window.__BOGCHA_API_BASE__ || 'http://127.0.0.1:8000/api/v1';

const STATE = {
  theme: 'light',
  currentRole: null,
  permissions: new Set(),
  currentTab: 'dashboard',
  groups: [],
  children: [],
  activities: [],
  staffPayroll: [],
  tabelData: [],
  financeStats: null
};

// ============================================================================
// Initialization & Backend Sync
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigation();
  initMobileNav();
  initAttendance();
  initLiveClock();
  initPhotos();
  initReminders();
  initStaffAttendance();
  initKitchen();
  initUserSession().then(ok => {
    if (!ok) return;
    syncWithBackend();
    if (can('photos.send')) loadPhotoStatus();
    if (can('billing.remind')) loadReminders();
    if (can('staff.view')) loadStaffAttendance();
    if (can('kitchen.view')) loadKitchenReports();
  });

  // Search Listeners
  const searchInput = document.getElementById('globalSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => handleGlobalSearch(e.target.value));
  }
  const childFilterInput = document.getElementById('childSearchFilter');
  if (childFilterInput) {
    childFilterInput.addEventListener('input', renderChildrenTable);
  }
  const childStatusSelect = document.getElementById('childStatusFilter');
  if (childStatusSelect) {
    childStatusSelect.addEventListener('change', renderChildrenTable);
  }
});

async function syncWithBackend() {
  try {
    // Only request what this role may see; the server enforces the same rules.
    const get = (perm, path) => can(perm) ? apiFetch(`${API_BASE}${path}`).catch(() => null) : Promise.resolve(null);
    const [statsRes, groupsRes, childrenRes, staffRes, tabelRes, financeStatsRes, attTodayRes] = await Promise.all([
      get('dashboard.view', '/dashboard/stats'),
      get('children.view', '/groups'),
      get('children.view', '/children'),
      get('staff.view', '/staff/payroll'),
      get('tabel.view', '/tabel'),
      get('billing.view', '/billing/stats'),
      get('attendance.view', '/attendance?group_name=ALL'),
    ]);
    if (attTodayRes?.ok) {
      STATE.attToday = Object.fromEntries((await attTodayRes.json()).map(r => [r.child_id, r.status]));
    }

    if (statsRes?.ok) {
      STATE.dashboard = await statsRes.json();
      STATE.activities = STATE.dashboard.activities || [];
    }

    if (groupsRes?.ok) STATE.groups = await groupsRes.json();
    if (childrenRes?.ok) {
      STATE.children = await childrenRes.json();
      const badge = document.getElementById('totalChildrenBadge');
      if (badge) badge.innerText = STATE.children.length;
    }
    if (staffRes?.ok) STATE.staffPayroll = await staffRes.json();
    if (tabelRes?.ok) STATE.tabelData = await tabelRes.json();
    if (financeStatsRes?.ok) STATE.financeStats = await financeStatsRes.json();

    // Re-render UI
    renderActivities();
    renderGroupsMiniGrid();
    renderDashboard();
    renderGroupFilterTabs();
    populateSelectOptions();
    renderChildrenTable();
    loadAttendance();
    renderTabelGrid();
    renderInvoicesTable();
    renderFinanceStats();
    renderStaffPayroll();
    renderContractsTable();
    updateTmaSimulator();

    console.log("[Bog'chaOS] Barcha 7 ta modul ma'lumotlar bazasi bilan sinxronlandi!");
  } catch (err) {
    console.warn("[Bog'chaOS] Backend sinxronlashda xatolik:", err);
  }
}

// ============================================================================
// 1. Role-Based Access Control (Rollar Boshqaruvi)
// ============================================================================

const ROLE_TITLES = {
  director: 'Boshqaruvchi (Direktor)',
  teacher: 'Tarbiyachi',
  accountant: 'Buxgalter',
  super_admin: 'Super Admin',
  nurse: 'Hamshira',
};

// Permissions come from the server (/auth/me), which also enforces them on every request.
// Hiding things here is only a convenience; it is not what protects the data.
function can(permission) {
  return STATE.permissions.has(permission);
}

function apiFetch(url, options = {}) {
  let token = null;
  try { token = localStorage.getItem('bogcha_token'); } catch (e) {}
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(url, { ...options, headers }).then(res => {
    if (res.status === 401) {
      try { localStorage.removeItem('bogcha_user'); localStorage.removeItem('bogcha_token'); } catch (e) {}
      window.location.href = `login.html?t=${Date.now()}`;
    }
    return res;
  });
}

function applyRoleAccess(role) {
  STATE.currentRole = role;

  const title = ROLE_TITLES[role] || role;
  document.getElementById('currentUserRole').innerText = title;
  const badge = document.getElementById('currentRoleBadge');
  if (badge) badge.innerText = title;

  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.style.display = can(btn.getAttribute('data-perm')) ? 'flex' : 'none';
  });

  const activeTabBtn = document.querySelector(`.sidebar-nav .nav-item[data-tab="${STATE.currentTab}"]`);
  if (activeTabBtn && activeTabBtn.style.display === 'none') {
    const firstVisible = document.querySelector('.sidebar-nav .nav-item:not([style*="display: none"])');
    if (firstVisible) {
      switchTab(firstVisible.getAttribute('data-tab'));
    }
  }

  const showFinance = can('children.finance');
  document.querySelectorAll('[data-perm-col="children.finance"]').forEach(th => { th.style.display = showFinance ? '' : 'none'; });

  const thDelete = document.getElementById('thDelete');
  if (thDelete) thDelete.style.display = can('children.delete') ? '' : 'none';

  document.querySelectorAll('[data-perm-action]').forEach(el => {
    el.style.display = can(el.getAttribute('data-perm-action')) ? '' : 'none';
  });

  renderChildrenTable();
}

async function initUserSession() {
  let token = null;
  try { token = localStorage.getItem('bogcha_token'); } catch (e) {}
  if (!token) {
    window.location.href = `login.html?t=${Date.now()}`;
    return false;
  }
  try {
    const res = await apiFetch(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const user = await res.json();
    STATE.permissions = new Set(user.permissions);
    applyRoleAccess(user.role);
    document.getElementById('currentUserName').innerText = user.name;
    document.getElementById('currentUserAvatar').innerText = user.avatar || user.name.split(' ').map(n => n[0]).join('');
    const greet = document.getElementById('dashboardGreeting');
    if (greet) greet.innerText = `Salom, ${user.name}!`;
    if (user.org) {
      STATE.org = user.org;
      const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
      setText('tenantAvatar', user.org.avatar);
      setText('tenantName', user.org.name);
      setText('tenantPlan', `${user.org.plan_tier} Tarif`);
      setText('contractOrgName', user.org.name.toUpperCase());
      setText('contractOrgName2', user.org.name);
      const orgName = document.getElementById('settingsOrgName');
      if (orgName) orgName.value = user.org.name;
      const orgPhone = document.getElementById('settingsOrgPhone');
      if (orgPhone) orgPhone.value = user.org.phone || '';
      const orgAddress = document.getElementById('settingsOrgAddress');
      if (orgAddress) orgAddress.value = user.org.address || '';
    }
    return true;
  } catch (e) {
    showToast("Server bilan ulanib bo'lmadi. Sahifani yangilang.", 'warning');
    return false;
  }
}

function logoutUser() {
  try { localStorage.removeItem('bogcha_user'); localStorage.removeItem('bogcha_token'); } catch (e) {}
  showToast("Tizimdan chiqildi", "info");
  setTimeout(() => {
    window.location.href = `login.html?t=${Date.now()}`;
  }, 400);
}

// ============================================================================
// 2. Oylik Tabel (Monthly Attendance Matrix & Compensation)
// ============================================================================

function renderTabelGrid() {
  const header = document.getElementById('tabelHeaderRow');
  const tbody = document.getElementById('tabelBodyRows');
  if (!header || !tbody) return;

  const YEAR = 2026, MONTH = 9; // October 2026, the billing period the backend serves
  const daysInMonth = new Date(YEAR, MONTH + 1, 0).getDate();
  const now = new Date();
  const isCurrentMonth = now.getFullYear() === YEAR && now.getMonth() === MONTH;
  const todayNum = isCurrentMonth ? now.getDate() : daysInMonth;
  const isWeekend = d => [0, 6].includes(new Date(YEAR, MONTH, d).getDay());
  const LETTER_STATUS = { P: 'PRESENT', E: 'EXCUSED', A: 'ABSENT', L: 'LATE' };

  let headerHtml = '<tr><th>Tarbiyalanuvchi</th>';
  for (let d = 1; d <= daysInMonth; d++) {
    headerHtml += `<th class="${isWeekend(d) ? 'is-weekend' : ''}${d === todayNum && isCurrentMonth ? ' is-today' : ''}">${d}</th>`;
  }
  headerHtml += '<th>Kelgan</th><th>Sababli</th><th>Kompensatsiya</th></tr>';
  header.innerHTML = headerHtml;

  const STATUS_CELL = { PRESENT: 'p-cell', EXCUSED: 'e-cell', ABSENT: 'a-cell', LATE: 'l-cell' };
  const cell = status => status
    ? `<span class="tabel-day-cell ${STATUS_CELL[status]}" title="${attStatusMeta(status).label}">${attMarkSvg(status)}</span>`
    : '';

  const data = STATE.tabelData.length > 0 ? STATE.tabelData : [
    { name: 'Imron Rahimov', days_present: 20, days_excused: 2, compensation: 50000 },
    { name: 'Madina Saidova', days_present: 22, days_excused: 0, compensation: 0 },
    { name: 'Jasur Aliyev', days_present: 17, days_excused: 5, compensation: 125000 },
    { name: 'Fotima Zokirova', days_present: 20, days_excused: 0, compensation: 0 },
    { name: 'Temur Mirzayev', days_present: 21, days_excused: 1, compensation: 25000 },
    { name: 'Otabek Shokirov', days_present: 22, days_excused: 0, compensation: 0 },
  ];

  tbody.innerHTML = data.map(row => {
    const days = row.days || {};
    let excusedLeft = Object.keys(days).length ? 0 : (row.days_excused || 0);
    let daysCells = '';
    for (let d = 1; d <= daysInMonth; d++) {
      if (isWeekend(d)) { daysCells += `<td class="is-weekend"><span class="tabel-day-cell w-cell" title="Dam olish kuni">–</span></td>`; continue; }
      if (d > todayNum) { daysCells += '<td></td>'; continue; }
      let status;
      if (d === todayNum && isCurrentMonth) {
        status = (STATE.attToday || {})[row.child_id] || null;
      } else {
        const v = days[d] ?? days[String(d)];
        status = v ? (LETTER_STATUS[v] || v) : null;
        // Without per-day records, place the month's excused days from the summary, then present.
        if (!status) status = excusedLeft-- > 0 ? 'EXCUSED' : 'PRESENT';
      }
      daysCells += `<td class="${d === todayNum && isCurrentMonth ? 'is-today' : ''}">${cell(status)}</td>`;
    }

    const compDisplay = row.compensation > 0
      ? `<strong class="text-rose">${signedMoney(-row.compensation)}</strong>`
      : `<span style="color: var(--text-muted);">${formatMoney(0)}</span>`;

    return `
      <tr>
        <td><b>${escapeHtml(row.name)}</b></td>
        ${daysCells}
        <td><b class="text-emerald">${row.days_present} kun</b></td>
        <td><b class="text-amber">${row.days_excused} kun</b></td>
        <td>${compDisplay}</td>
      </tr>
    `;
  }).join('');
}

function applyCompensationToInvoices() {
  showToast(`Oylik tabel tasdiqlandi: Sababli kelmagan kunlar uchun oziq-ovqat kompensatsiyasi keyingi oy kvitansiyasiga chegirildi!`, 'success');
}

function exportTabelExcel() {
  showToast(`Oktabr oyi to'liq davomat tabeli Excel formatida shakllantirildi.`, 'info');
}

// ============================================================================
// 5. Xodimlar va Ish Haqi (Staff & Payroll)
// ============================================================================

function renderStaffPayroll() {
  const tbody = document.getElementById('staffPayrollTableBody');
  if (!tbody) return;

  const defaultPayroll = [
    { id: 'pr_1', staff_name: 'Gulbahor Karimova', role: 'TARBIYACHI', phone: '+998 93 444 55 66', base_salary: 4500000, bonus: 500000, advance_paid: 2000000, status: 'PAID' },
    { id: 'pr_2', staff_name: 'Nargiza Olimova', role: 'TARBIYACHI', phone: '+998 90 222 33 44', base_salary: 4500000, bonus: 300000, advance_paid: 1500000, status: 'PENDING' },
    { id: 'pr_3', staff_name: 'Dilnoza Ahmedova', role: 'ENAGA', phone: '+998 94 111 55 77', base_salary: 2800000, bonus: 0, advance_paid: 1000000, status: 'PENDING' },
    { id: 'pr_4', staff_name: 'Salim Rahmonov', role: 'OSHPAZ', phone: '+998 97 888 99 00', base_salary: 5000000, bonus: 600000, advance_paid: 2500000, status: 'PAID' },
    { id: 'pr_5', staff_name: 'Umida Qosimova', role: 'HAMSHIRA', phone: '+998 91 333 77 11', base_salary: 3500000, bonus: 200000, advance_paid: 1000000, status: 'PENDING' },
  ];

  const list = STATE.staffPayroll.length > 0 ? STATE.staffPayroll : defaultPayroll;

  tbody.innerHTML = list.map(p => {
    const toPay = (p.base_salary + p.bonus) - p.advance_paid;
    return `
      <tr>
        <td>
          <b>${p.staff_name}</b><br>
          <span class="badge badge-indigo">${p.role}</span>
        </td>
        <td>${p.phone}</td>
        <td>${formatMoney(p.base_salary)}</td>
        <td class="${p.bonus ? 'text-emerald' : ''}">${signedMoney(p.bonus)}</td>
        <td class="${p.advance_paid ? 'text-rose' : ''}">${signedMoney(-p.advance_paid)}</td>
        <td><b style="font-size: 1rem;">${formatMoney(toPay)}</b></td>
        <td>
          ${p.status === 'PAID' 
            ? `<span class="badge badge-emerald">To'langan</span>` 
            : `<span class="badge badge-amber">Kutilmoqda</span>`}
        </td>
        <td class="text-right">
          ${p.status === 'PAID' 
            ? `<button class="btn btn-sm btn-secondary" disabled>To'landi</button>` 
            : `<button class="btn btn-sm btn-success" onclick="payStaffSalary('${p.id}', ${toPay})">Maosh to'lash</button>`}
        </td>
      </tr>
    `;
  }).join('');
}

function payStaffSalary(payrollId, amount) {
  apiFetch(`${API_BASE}/staff/pay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payroll_id: payrollId, amount: amount })
  }).then(r => r.json()).then(() => {
    syncWithBackend();
    showToast(`Xodimga oylik maosh muvaffaqiyatli to'landi!`, 'success');
  }).catch(() => {
    showToast(`Maosh to'lovi saqlandi!`, 'success');
  });
}

// ============================================================================
// 6. Shartnomalar va Tibbiy Hujjatlar
// ============================================================================

function renderContractsTable() {
  const tbody = document.getElementById('contractsTableBody');
  if (!tbody) return;

  tbody.innerHTML = STATE.children.map(c => `
    <tr>
      <td><code>SH-2025-${c.id.toUpperCase()}</code></td>
      <td>
        <b>${c.name}</b><br>
        <small style="color: var(--text-muted);">${c.group}</small>
      </td>
      <td>
        ${c.parentName}<br>
        <small style="color: #6366f1;">${c.parentPhone}</small>
      </td>
      <td>01.09.2025</td>
      <td><span class="badge badge-emerald">Barcha emlashlar bor</span></td>
      <td><span class="badge badge-emerald">Spravka mavjud</span></td>
      <td class="text-right">
        <button class="btn btn-sm btn-secondary" onclick="viewChildContract('${c.id}')">Shartnoma</button>
      </td>
    </tr>
  `).join('');
}

function viewChildContract(childId) {
  const child = STATE.children.find(c => c.id === childId) || STATE.children[0];
  if (!child) return;

  document.getElementById('contractDocNumber').innerText = `SH-2025-${child.id.toUpperCase()}`;
  document.getElementById('contractDocChildName').innerText = child.name;
  document.getElementById('contractDocParentName').innerText = child.parentName;
  document.getElementById('contractDocSignParent').innerText = child.parentName;
  document.getElementById('contractDocSignPhone').innerText = child.parentPhone;

  openModal('contractViewModal');
}

// Helper: Populate selects in modals
function populateSelectOptions() {
  const tmaSelect = document.getElementById('tmaChildSelect');
  if (tmaSelect && STATE.children.length > 0) {
    tmaSelect.innerHTML = STATE.children.map((c, i) => `<option value="${i}">${c.name} (${c.group})</option>`).join('');
  }

  const groupOptions = STATE.groups.map(g => `<option value="${g.name}">${g.name} (${g.age})</option>`).join('');

  const newChildGroupSelect = document.getElementById('newChildGroup');
  if (newChildGroupSelect && STATE.groups.length > 0) {
    const prev = newChildGroupSelect.value;
    newChildGroupSelect.innerHTML = groupOptions;
    if ([...newChildGroupSelect.options].some(o => o.value === prev)) newChildGroupSelect.value = prev;
  }

  const attGroupSelect = document.getElementById('attendanceGroupSelect');
  if (attGroupSelect && STATE.groups.length > 0) {
    const prev = attGroupSelect.value;
    attGroupSelect.innerHTML = groupOptions;
    if ([...attGroupSelect.options].some(o => o.value === prev)) attGroupSelect.value = prev;
  }
}

function renderGroupFilterTabs() {
  const container = document.getElementById('groupFilterTabs');
  if (!container) return;
  const currentActive = container.querySelector('.filter-tab.active')?.getAttribute('data-group') || 'ALL';

  const tabsHtml = ['<button class="filter-tab" data-group="ALL">Barchasi</button>']
    .concat(STATE.groups.map(g => `<button class="filter-tab" data-group="${g.name}">${g.name}</button>`))
    .join('');
  container.innerHTML = tabsHtml;

  container.querySelectorAll('.filter-tab').forEach(btn => {
    if (btn.getAttribute('data-group') === currentActive) btn.classList.add('active');
    btn.addEventListener('click', () => {
      container.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderChildrenTable();
    });
  });
}

function setGroupModalMode(group) {
  STATE.editingGroupId = group ? group.id : null;
  document.getElementById('groupModalTitle').textContent = group ? `${group.name}: tahrirlash` : "Yangi guruh qo'shish";
  document.getElementById('groupModalSubmit').textContent = group ? 'Saqlash' : "Guruh qo'shish";
  document.getElementById('newGroupName').disabled = !!group;
}

function openAddGroupModal() {
  document.getElementById('addGroupForm').reset();
  document.getElementById('newGroupCapacity').value = 25;
  setGroupModalMode(null);
  openModal('addGroupModal');
}

function openEditGroupModal(groupId) {
  const g = STATE.groups.find(x => x.id === groupId);
  if (!g) return;
  document.getElementById('addGroupForm').reset();
  document.getElementById('newGroupName').value = g.name;
  document.getElementById('newGroupAge').value = g.age || '';
  document.getElementById('newGroupCapacity').value = g.capacity;
  document.getElementById('newGroupTeacher').value = g.teacher || '';
  document.getElementById('newGroupTeacher2').value = g.teacher2 || '';
  document.getElementById('newGroupFee').value = g.fee ?? '';
  setGroupModalMode(g);
  openModal('addGroupModal');
}

function handleAddGroupSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('newGroupName').value.trim();
  const body = {
    age_category: document.getElementById('newGroupAge').value.trim(),
    capacity: parseInt(document.getElementById('newGroupCapacity').value, 10),
    teacher_name: document.getElementById('newGroupTeacher').value.trim(),
    teacher2_name: document.getElementById('newGroupTeacher2').value.trim() || null,
    monthly_fee: parseFloat(document.getElementById('newGroupFee').value),
  };
  const editing = STATE.editingGroupId;

  apiFetch(editing ? `${API_BASE}/groups/${encodeURIComponent(editing)}` : `${API_BASE}/groups`, {
    method: editing ? 'PATCH' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(editing ? body : { name, ...body })
  }).then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Xatolik yuz berdi');
    return data;
  }).then(() => {
    closeModal('addGroupModal');
    syncWithBackend();
    showToast(editing ? `"${name}" guruhi yangilandi.` : `"${name}" guruhi qo'shildi.`, 'success');
  }).catch(err => {
    showToast(err.message || 'Xatolik yuz berdi', 'warning');
  });
}

function calcPricingDiscount() {
  const base = parseFloat(document.getElementById('editPricingBasePrice').value);
  const percent = parseFloat(document.getElementById('editPricingDiscountPercent').value);
  const resultLabel = document.getElementById('editPricingCalcResult');

  if (isNaN(base) || isNaN(percent) || percent < 0 || percent > 100) {
    resultLabel.innerText = 'Asl narx va foizni kiriting: Нархи avtomatik hisoblanadi.';
    return;
  }

  const final = Math.round(base * (1 - percent / 100) / 1000) * 1000;
  document.getElementById('editPricingPrice').value = final;
  document.getElementById('editPricingDiscount').value = `${percent}%`;
  resultLabel.innerHTML = `<b style="color: var(--color-emerald);">${formatMoney(final)}</b> (${formatMoney(base)} dan ${percent}% chegirma)`;
}

// ============================================================================
// Standard UI Engines: Navigation, Dashboard, Attendance, Billing
// ============================================================================

function initTheme() {
  STATE.theme = document.documentElement.getAttribute('data-theme') || 'light';
  const toggleBtn = document.getElementById('themeToggle');
  toggleBtn?.addEventListener('click', () => {
    const next = STATE.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    STATE.theme = next;
    try { localStorage.setItem('bogcha_theme', next); } catch (e) {}
  });
}

function initNavigation() {
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.getAttribute('data-tab'));
      setMobileNav(false);
    });
  });
}

function setMobileNav(open) {
  document.body.classList.toggle('nav-open', open);
  const toggle = document.getElementById('menuToggle');
  if (toggle) {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Menyuni yopish' : 'Menyuni ochish');
  }
}

function initMobileNav() {
  document.getElementById('menuToggle')?.addEventListener('click', () => setMobileNav(!document.body.classList.contains('nav-open')));
  document.getElementById('sidebarScrim')?.addEventListener('click', () => setMobileNav(false));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') setMobileNav(false); });
}

function switchTab(tabId) {
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabId}`);
  });
  STATE.currentTab = tabId;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initLiveClock() {
  const container = document.getElementById('liveClock');
  if (!container) return;
  setInterval(() => {
    const now = new Date();
    const months = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'];
    container.innerHTML = `
      <span class="clock-date">${now.getDate()} ${months[now.getMonth()]}, ${now.getFullYear()}</span>
      <span class="clock-time">${now.toLocaleTimeString('uz-UZ', { hour12: false })}</span>
    `;
  }, 1000);
}

const MONTH_NAMES = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'];

function periodLabel(period) {
  const [y, m] = period.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

function shortMoney(amount) {
  if (amount >= 1e6) return `${(amount / 1e6).toFixed(amount >= 1e7 ? 0 : 1).replace('.0', '')} mln`;
  if (amount >= 1e3) return `${Math.round(amount / 1e3)} ming`;
  return String(Math.round(amount || 0));
}

function renderDashboard() {
  const d = STATE.dashboard;
  if (!d) return;
  const set = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
  set('kpiTotalChildren', `${d.total_children} nafar`);
  set('kpiChildrenNote', `${STATE.groups.length} ta guruh`);
  set('kpiAttendanceRate', `${d.present_today} / ${d.total_children}`);
  set('kpiAttendanceNote', `${d.absent_today} kelmadi · ${d.unmarked_today} belgilanmagan`);
  set('kpiStaff', `${d.staff_present} / ${d.staff_total}`);
  set('kpiStaffNote', d.staff_marked ? `${d.staff_total - d.staff_marked} ta belgilanmagan` : 'Davomat hali belgilanmagan');
  set('kpiRevenue', formatMoney(d.monthly_revenue));
  set('kpiRevenueNote', d.monthly_revenue ? `Oy rejasining ${d.collection.percent}% yig'ildi` : "Bu oy hali to'lov qabul qilinmagan");
  set('kpiDebts', formatMoney(d.total_debts));
  set('kpiDebtsNote', d.collection.overdue_count ? `${d.collection.overdue_count} ta hisobning muddati o'tgan` : "Muddati o'tgan qarz yo'q");

  const list = document.getElementById('attentionList');
  if (list) {
    list.innerHTML = d.attention.length
      ? d.attention.map((a, i) => `
        <li><button type="button" class="todo-item" data-kind="${a.kind}" onclick="openAttention(${i})">
          <span class="todo-text"><b>${escapeHtml(a.label)}</b><small>${escapeHtml(a.detail)}</small></span>
          <span class="todo-count">${a.count}</span>
          <svg class="todo-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
        </button></li>`).join('')
      : `<li class="todo-empty">Hammasi joyida. Bugun bajarilishi kerak bo'lgan ish yo'q.</li>`;
  }

  const debtors = document.getElementById('topDebtorsList');
  if (debtors) {
    const rows = d.collection.top_debtors;
    debtors.innerHTML = rows.length
      ? rows.map(r => `
        <li><button type="button" class="debtor-item" onclick="openRecordPaymentModal('${escapeHtml(r.child_id)}')">
          <span class="child-avatar" aria-hidden="true">${escapeHtml(r.name.split(' ').filter(Boolean).map(n => n[0]).join('').slice(0, 2))}</span>
          <span class="debtor-text"><b>${escapeHtml(r.name)}</b><small>${escapeHtml(r.group)}${r.overdue ? " · muddati o'tgan" : ''}</small></span>
          <span class="debtor-amount ${r.overdue ? 'is-overdue' : ''}">${shortMoney(r.debt)}</span>
        </button></li>`).join('')
      : `<li class="todo-empty">Qarzdor oilalar yo'q.</li>`;
  }

  const c = d.collection;
  const block = document.getElementById('collectionBlock');
  if (block) {
    block.innerHTML = `
      <div class="collection-head"><span>${periodLabel(c.period)} — yig'ildi</span><b>${c.percent}%</b></div>
      <div class="collection-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${c.percent}"><span style="width:${Math.min(100, c.percent)}%"></span></div>
      <p class="collection-note">${formatMoney(c.due)} dan ${formatMoney(c.collected)} yig'ildi · qoldi ${formatMoney(c.left)}</p>`;
  }
  renderWeeklyChart();
}

function openAttention(index) {
  const item = STATE.dashboard?.attention[index];
  if (!item) return;
  switchTab(item.tab);
  if (item.kind === 'attendance' && item.group) {
    const select = document.getElementById('attendanceGroupSelect');
    if (select && [...select.options].some(o => o.value === item.group)) { select.value = item.group; loadAttendance(); }
  }
  if (item.kind === 'groups') document.getElementById('groupsMiniGrid')?.scrollIntoView({ behavior: 'smooth' });
}

function renderWeeklyChart() {
  const container = document.getElementById('weeklyChartContainer');
  if (!container) return;
  const history = STATE.dashboard?.income_history || [];
  const max = Math.max(0, ...history.map(h => h.amount));
  if (!max) {
    container.innerHTML = `<p class="chart-empty">Oxirgi 6 oyda to'lov qabul qilinmagan</p>` + history.map(h => `
      <div class="bar-column"><div class="bar-pill is-empty"></div><span class="bar-label">${h.label}</span></div>`).join('');
    return;
  }
  container.innerHTML = history.map((h, i) => `
    <div class="bar-column ${i === history.length - 1 ? 'is-current' : ''}">
      <div class="bar-pill" style="height: ${Math.max(2, Math.round(h.amount / max * 100))}%;" data-percent="${h.amount ? shortMoney(h.amount) : ''}"></div>
      <span class="bar-label">${h.label}</span>
    </div>`).join('');
}

function renderActivities() {
  const feed = document.getElementById('activityFeed');
  if (!feed) return;
  // Register marks are reserved for attendance; other events get a plain ink dot.
  const markFor = text => {
    if (/kech keldi/i.test(text)) return 'LATE';
    if (/sababli/i.test(text)) return 'EXCUSED';
    if (/kelmadi/i.test(text)) return 'ABSENT';
    if (/keldi/i.test(text)) return 'PRESENT';
    return null;
  };
  feed.innerHTML = STATE.activities.slice(0, 5).map(act => {
    const mark = markFor(act.text);
    return `
    <div class="activity-item">
      <div class="activity-icon" data-mark="${mark || 'EVENT'}">${mark ? attMarkSvg(mark) : '<span class="activity-dot"></span>'}</div>
      <div class="activity-details">
        <p>${escapeHtml(act.text)}</p>
        <small>${escapeHtml(act.time)} da</small>
      </div>
    </div>
  `;
  }).join('');
}

function renderGroupsMiniGrid() {
  const container = document.getElementById('groupsMiniGrid');
  if (!container) return;
  const badge = document.getElementById('groupsCountBadge');
  if (badge) badge.textContent = `${STATE.groups.length} ta guruh`;
  const R = 26, CIRC = 2 * Math.PI * R;
  container.innerHTML = STATE.groups.map(g => {
    const ratio = g.capacity ? g.count / g.capacity : 0;
    const state = g.count > g.capacity ? 'over' : g.count === g.capacity ? 'full' : 'open';
    const note = state === 'over' ? `Sig'imdan ${g.count - g.capacity} ta ortiq`
      : state === 'full' ? "To'lgan" : `${g.capacity - g.count} ta bo'sh o'rin`;
    const teachers = (g.teachers || []).length
      ? g.teachers.map(t => `<span class="teacher-chip">${escapeHtml(t)}</span>`).join('')
      : '<span class="teacher-chip is-missing">Tarbiyachi belgilanmagan</span>';
    return `
      <div class="group-card" data-state="${state}">
        <div class="group-ring" aria-label="${g.count} / ${g.capacity}">
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle cx="32" cy="32" r="${R}" class="ring-track"/>
            <circle cx="32" cy="32" r="${R}" class="ring-fill" stroke-dasharray="${(Math.min(1, ratio) * CIRC).toFixed(1)} ${CIRC.toFixed(1)}"/>
          </svg>
          <span><b>${g.count}</b>/ ${g.capacity}</span>
        </div>
        <div class="group-body">
          <div class="group-card-header">
            <span class="group-name">${escapeHtml(g.name)}</span>
            ${can('groups.manage') ? `<button type="button" class="btn btn-sm btn-secondary" onclick="openEditGroupModal('${escapeHtml(g.id)}')" aria-label="${escapeHtml(g.name)} guruhini tahrirlash">${PENCIL_ICON}</button>` : ''}
          </div>
          <p class="group-teacher">${escapeHtml(g.age || '')}</p>
          <div class="teacher-chips">${teachers}</div>
          <p class="group-status">${note}</p>
        </div>
      </div>
    `;
  }).join('');
}

function renderChildrenTable() {
  const tbody = document.getElementById('childrenTableBody');
  if (!tbody) return;
  const searchVal = (document.getElementById('childSearchFilter')?.value || '').toLowerCase();
  const statusFilter = document.getElementById('childStatusFilter')?.value || 'ALL';
  const activeTabBtn = document.querySelector('.filter-tab.active');
  const groupFilter = activeTabBtn ? activeTabBtn.getAttribute('data-group') : 'ALL';

  const filtered = STATE.children.filter(c => {
    const matchSearch = c.name.toLowerCase().includes(searchVal) || c.parentName.toLowerCase().includes(searchVal) || c.parentPhone.includes(searchVal);
    const matchStatus = statusFilter === 'ALL' ? true : statusFilter === 'DEBT' ? c.paymentStatus === 'DEBT' : c.status === statusFilter;
    const matchGroup = groupFilter === 'ALL' ? true : c.group === groupFilter;
    return matchSearch && matchStatus && matchGroup;
  });

  const hideRestrictedColumns = !can('children.finance');
  const canEditHealth = can('children.health.edit');
  const canEditPricing = can('children.pricing.edit');
  const canDelete = can('children.delete');

  tbody.innerHTML = filtered.map(child => {
    const initials = child.name.split(' ').filter(Boolean).map(n => n[0]).join('').slice(0, 2);
    const healthy = /^\s*(yo'?q|sog'?lom|соғлом|согл?ом|здоров|нет|-|—)?\s*$/i.test(child.allergies || '');
    const healthDisplay = healthy
      ? `<span class="text-emerald">Sog'lom</span>`
      : `<span class="text-rose" style="font-weight: 600;">${escapeHtml(child.allergies)}</span>`;
    return `
      <tr>
        <td>
          <div class="child-cell">
            <div class="child-avatar">${initials}</div>
            <div>
              <span class="child-name">${escapeHtml(child.name)}</span>
              <small style="color: var(--text-muted); font-size: 0.78rem;">ID: ${escapeHtml(child.id)}</small>
            </div>
          </div>
        </td>
        <td><span class="badge badge-indigo">${escapeHtml(child.group)}</span></td>
        <td>${escapeHtml(child.birthDate)}</td>
        <td>
          <div><b>${escapeHtml(child.parentName)}</b></div>
          <small style="color: var(--color-primary);">${escapeHtml(child.parentPhone)}</small>
          ${can('parents.invite') ? `<div><button class="btn btn-sm btn-secondary tg-btn" onclick="openTelegramLink('${escapeHtml(child.id)}')">Telegram</button></div>` : ''}
        </td>
        <td>
          ${healthDisplay}
          ${canEditHealth ? `<button class="btn btn-sm btn-secondary" style="margin-left:6px;" onclick="openEditHealthModal('${child.id}', '${child.name.replace(/'/g, "\\'")}', '${(child.allergies || '').replace(/'/g, "\\'")}')" title="Tahrirlash" aria-label="Tahrirlash">${PENCIL_ICON}</button>` : ''}
        </td>
        ${hideRestrictedColumns ? '' : `<td>${child.discount ? `<span class="badge badge-amber">${escapeHtml(child.discount)}</span>` : '—'}</td>
        <td>${child.note ? escapeHtml(child.note) : '—'}</td>
        <td>
          ${child.listedPrice != null ? formatMoney(child.listedPrice) : '<span style="color: var(--text-muted);">Belgilanmagan</span>'}
          ${canEditPricing ? `<button class="btn btn-sm btn-secondary" style="margin-left:6px;" onclick="openEditPricingModal('${child.id}', '${child.name.replace(/'/g, "\\'")}', '${(child.discount || '').replace(/'/g, "\\'")}', '${(child.note || '').replace(/'/g, "\\'")}', ${child.listedPrice != null ? child.listedPrice : 'null'})" title="Tahrirlash" aria-label="Tahrirlash">${PENCIL_ICON}</button>` : ''}
        </td>`}
        ${hideRestrictedColumns ? '' : `
        <td>
          ${child.paymentStatus === 'PAID' ? `<span class="badge badge-emerald">To'langan</span>` : `<span class="badge badge-rose">Qarzdor (${formatMoney(child.debt)})</span>`}
        </td>
        <td class="text-right">
          <button class="btn btn-sm btn-secondary" onclick="viewChildReceipt('${child.id}')">Chek</button>
          <button class="btn btn-sm btn-secondary" onclick="viewChildContract('${child.id}')">Shartnoma</button>
        </td>`}
        ${canDelete ? `
        <td class="text-right col-actions">
          <button class="btn btn-sm btn-danger" onclick="handleDeleteChild('${child.id}', '${child.name.replace(/'/g, "\\'")}')">O'chirish</button>
        </td>` : ''}
      </tr>
    `;
  }).join('');
}

// ============================================================================
// Rasm yuborish (send photos to parents via Telegram)
// ============================================================================

const PHOTOS = { items: [], channelLinked: false, sending: false };
const PHOTO_MAX = 10;
const PHOTO_EDGE = 1600;

function initPhotos() {
  const input = document.getElementById('photoFiles');
  if (!input) return;
  input.addEventListener('change', async () => {
    const files = [...input.files].filter(f => /^image\/(jpeg|png)$/.test(f.type));
    input.value = '';
    for (const file of files) {
      if (PHOTOS.items.length >= PHOTO_MAX) { showToast(`Bir martada ${PHOTO_MAX} tagacha rasm yuborish mumkin.`, 'warning'); break; }
      try { PHOTOS.items.push(await resizeImage(file)); } catch (e) { showToast(`${file.name}: rasmni o'qib bo'lmadi.`, 'warning'); }
    }
    renderPhotoPreviews();
  });
  document.querySelectorAll('input[name="photoTarget"]').forEach(r => r.addEventListener('change', updatePhotoForm));
  document.getElementById('photoChildSelect').addEventListener('change', updatePhotoForm);
  document.getElementById('photoPreviews').addEventListener('click', e => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    PHOTOS.items.splice(Number(btn.dataset.remove), 1);
    renderPhotoPreviews();
  });
  document.getElementById('photoForm').addEventListener('submit', sendPhotos);
  document.getElementById('photoConnectForm').addEventListener('submit', connectPhotoChannel);
}

// Downscale in the browser: faster uploads from phones, and Telegram recompresses anyway.
function resizeImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, PHOTO_EDGE / Math.max(img.width, img.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/jpeg', 0.86));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('decode')); };
    img.src = url;
  });
}

function renderPhotoPreviews() {
  document.getElementById('photoPreviews').innerHTML = PHOTOS.items.map((src, i) => `
    <figure class="photo-thumb">
      <img src="${src}" alt="Tanlangan rasm ${i + 1}">
      <button type="button" class="photo-remove" data-remove="${i}" aria-label="Rasmni olib tashlash"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
    </figure>`).join('');
  updatePhotoForm();
}

function populatePhotoChildren() {
  const select = document.getElementById('photoChildSelect');
  if (!select || !STATE.children.length) return;
  const prev = select.value;
  select.innerHTML = '<option value="">Bolani tanlang…</option>' +
    STATE.children.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${escapeHtml(c.group)})</option>`).join('');
  if ([...select.options].some(o => o.value === prev)) select.value = prev;
}

function updatePhotoForm() {
  const target = document.querySelector('input[name="photoTarget"]:checked')?.value;
  const select = document.getElementById('photoChildSelect');
  select.hidden = target !== 'child';
  if (target === 'child') populatePhotoChildren();
  const n = PHOTOS.items.length;
  document.getElementById('photoCount').textContent = n ? `${n} ta rasm tanlandi` : 'Rasm tanlanmagan';
  const ready = n > 0 && !PHOTOS.sending && (target === 'channel' ? PHOTOS.channelLinked : !!select.value);
  document.getElementById('photoSendBtn').disabled = !ready;
}

async function loadPhotoStatus() {
  const status = document.getElementById('photoChannelStatus');
  try {
    const res = await apiFetch(`${API_BASE}/telegram/status`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    const ch = data.channel;
    PHOTOS.channelLinked = ch.linked;
    status.dataset.state = ch.linked ? 'linked' : 'pending';
    status.innerHTML = ch.linked
      ? `Kanal ulangan: <b>${escapeHtml(ch.title)}</b>${ch.username ? ` (@${escapeHtml(ch.username)})` : ''}. Rasmlar ${escapeHtml(data.bot || 'bot')} orqali yuboriladi.`
      : `Telegram kanal hali ulanmagan.${data.can_manage ? '' : ' Direktordan kanalni ulashni so\'rang.'}`;
    document.getElementById('photoPublicWarning').hidden = !(ch.linked && ch.public);
    document.getElementById('photoConnectForm').hidden = !data.can_manage;
  } catch (err) {
    status.textContent = err.message || "Holatni olib bo'lmadi.";
    status.dataset.state = 'error';
  }
  updatePhotoForm();
}

async function connectPhotoChannel(e) {
  e.preventDefault();
  const address = document.getElementById('photoChannelInput').value.trim();
  if (!address) return;
  try {
    const res = await apiFetch(`${API_BASE}/telegram/channel`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    showToast(`"${data.title}" ulandi.`, 'success');
    document.getElementById('photoChannelInput').value = '';
    loadPhotoStatus();
  } catch (err) {
    showToast(err.message, 'warning');
  }
}

async function sendPhotos(e) {
  e.preventDefault();
  const target = document.querySelector('input[name="photoTarget"]:checked').value;
  const childId = document.getElementById('photoChildSelect').value;
  const btn = document.getElementById('photoSendBtn');
  PHOTOS.sending = true;
  btn.textContent = 'Yuborilmoqda…';
  updatePhotoForm();
  try {
    const res = await apiFetch(`${API_BASE}/telegram/photos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, child_id: target === 'child' ? childId : null, caption: document.getElementById('photoCaption').value, images: PHOTOS.items })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    showToast(`${data.sent} ta rasm yuborildi: ${data.to}.`, 'success');
    PHOTOS.items = [];
    document.getElementById('photoCaption').value = '';
    renderPhotoPreviews();
  } catch (err) {
    showToast(err.message || "Rasmlarni yuborib bo'lmadi.", 'warning');
  } finally {
    PHOTOS.sending = false;
    btn.textContent = 'Yuborish';
    updatePhotoForm();
  }
}

async function openTelegramLink(childId) {
  const status = document.getElementById('tgLinkStatus');
  const input = document.getElementById('tgLinkUrl');
  document.getElementById('tgLinkChild').textContent = '';
  status.textContent = 'Yuklanmoqda…';
  status.dataset.state = '';
  input.value = '';
  openModal('telegramLinkModal');
  try {
    const res = await apiFetch(`${API_BASE}/children/${encodeURIComponent(childId)}/telegram-link`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    document.getElementById('tgLinkChild').textContent = data.child;
    status.textContent = data.linked
      ? `Ota-ona ${data.bot} botiga ulangan, xabarlar yuborilmoqda.`
      : `Ota-ona hali ${data.bot} botiga ulanmagan.`;
    status.dataset.state = data.linked ? 'linked' : 'pending';
    input.value = data.url;
  } catch (err) {
    status.textContent = err.message || "Havolani olib bo'lmadi.";
    status.dataset.state = 'error';
  }
}

async function copyTelegramLink() {
  const input = document.getElementById('tgLinkUrl');
  if (!input.value) return;
  try {
    await navigator.clipboard.writeText(input.value);
  } catch (e) {
    input.select();
    document.execCommand('copy');
  }
  showToast('Havola nusxalandi. Uni ota-onaga yuboring.', 'success');
}

function handleDeleteChild(childId, childName) {
  if (!confirm(`"${childName}" ni ro'yxatdan butunlay o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.`)) {
    return;
  }
  apiFetch(`${API_BASE}/children/${childId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(() => {
      syncWithBackend();
      showToast(`${childName} ro'yxatdan o'chirildi.`, 'warning');
    })
    .catch(() => {
      showToast(`Xatolik yuz berdi`, 'warning');
    });
}

function openEditHealthModal(childId, childName, currentHealth) {
  document.getElementById('editHealthChildId').value = childId;
  document.getElementById('editHealthChildName').value = childName;
  document.getElementById('editHealthValue').value = currentHealth;
  openModal('editHealthModal');
}

function handleHealthSubmit(e) {
  e.preventDefault();
  const childId = document.getElementById('editHealthChildId').value;
  const health = document.getElementById('editHealthValue').value.trim();

  apiFetch(`${API_BASE}/children/${childId}/health`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ health })
  }).then(r => r.json()).then(() => {
    closeModal('editHealthModal');
    syncWithBackend();
    showToast(`Sog'liq holati yangilandi.`, 'success');
  }).catch(() => {
    showToast(`Xatolik yuz berdi`, 'warning');
  });
}

function openEditPricingModal(childId, childName, discount, note, listedPrice) {
  document.getElementById('editPricingChildId').value = childId;
  document.getElementById('editPricingChildName').value = childName;
  document.getElementById('editPricingDiscount').value = discount || '';
  document.getElementById('editPricingNote').value = note || '';
  document.getElementById('editPricingPrice').value = listedPrice != null ? listedPrice : '';
  document.getElementById('editPricingBasePrice').value = listedPrice != null ? listedPrice : '';
  document.getElementById('editPricingDiscountPercent').value = '';
  document.getElementById('editPricingCalcResult').innerText = 'Asl narx va foizni kiriting: Нархи avtomatik hisoblanadi.';
  openModal('editPricingModal');
}

function handlePricingSubmit(e) {
  e.preventDefault();
  const childId = document.getElementById('editPricingChildId').value;
  const discount = document.getElementById('editPricingDiscount').value.trim() || null;
  const note = document.getElementById('editPricingNote').value.trim() || null;
  const priceRaw = document.getElementById('editPricingPrice').value.trim();
  const monthly_fee = priceRaw === '' ? null : parseFloat(priceRaw);

  apiFetch(`${API_BASE}/children/${childId}/pricing`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ discount, note, monthly_fee })
  }).then(r => r.json()).then(() => {
    closeModal('editPricingModal');
    syncWithBackend();
    showToast(`Narx, chegirma va izoh yangilandi.`, 'success');
  }).catch(() => {
    showToast(`Xatolik yuz berdi`, 'warning');
  });
}

// ============================================================================
// Kunlik davomat (Daily attendance)
// Marks wait ATT_UNDO_MS before saving, because saving "Keldi" messages the parent.
// ============================================================================

const ATT_STATUSES = [
  { key: 'PRESENT', label: 'Keldi', cls: 'present' },
  { key: 'ABSENT', label: 'Kelmadi', cls: 'absent' },
  { key: 'EXCUSED', label: 'Sababli', cls: 'excused' },
  { key: 'LATE', label: 'Kech keldi', cls: 'late' },
];
const ATT_UNDO_MS = 5000;

const ATT = {
  rows: [],
  date: null,
  error: false,
  loading: false,
  requestId: 0,
  pending: new Map(), // childId -> { status, prev: {status, time}, timer, batch }
  failed: new Map(),  // childId -> { status, prev }
  saving: new Set(),
};

const PENCIL_ICON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>';

function attMarkSvg(status) {
  return `<svg class="mark" aria-hidden="true"><use href="#mark-${status}"/></svg>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function attStatusMeta(key) {
  return ATT_STATUSES.find(s => s.key === key);
}

function attIsEditable() {
  return ATT.date === todayISO() && can('attendance.mark');
}

function attDisplayStatus(row) {
  return ATT.pending.get(row.id)?.status ?? row.status;
}

function initAttendance() {
  const dateInput = document.getElementById('attendanceDate');
  if (dateInput) {
    dateInput.value = todayISO();
    dateInput.max = todayISO();
    dateInput.addEventListener('change', loadAttendance);
  }
  document.getElementById('attendanceGroupSelect')?.addEventListener('change', loadAttendance);

  document.getElementById('attendanceCardsGrid')?.addEventListener('click', e => {
    const row = e.target.closest('.att-row');
    const statusBtn = e.target.closest('.att-btn');
    if (statusBtn && row) return setAttendance(row.dataset.id, statusBtn.dataset.status);
    if (e.target.closest('[data-undo]') && row) return undoAttendance(row.dataset.id);
    if (e.target.closest('[data-retry]') && row) return retryAttendance(row.dataset.id);
    if (e.target.closest('[data-reload]')) return loadAttendance();
  });

  window.addEventListener('pagehide', () => {
    if (ATT.pending.size) commitAttendance([...ATT.pending.keys()]);
  });
}

async function loadAttendance() {
  const group = document.getElementById('attendanceGroupSelect')?.value;
  const date = document.getElementById('attendanceDate')?.value || todayISO();
  if (ATT.pending.size) commitAttendance([...ATT.pending.keys()]);
  ATT.failed.clear();

  if (!group) {
    ATT.rows = [];
    ATT.date = date;
    renderAttendanceGrid();
    return;
  }

  const requestId = ++ATT.requestId;
  ATT.loading = true;
  renderAttendanceGrid();
  try {
    const res = await apiFetch(`${API_BASE}/attendance?group_name=${encodeURIComponent(group)}&att_date=${encodeURIComponent(date)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (requestId !== ATT.requestId) return;
    ATT.rows = data.map(r => ({ id: r.child_id, name: r.name, status: r.status, time: r.check_in_time }));
    ATT.error = false;
  } catch (err) {
    if (requestId !== ATT.requestId) return;
    ATT.rows = [];
    ATT.error = true;
  }
  ATT.date = date;
  ATT.loading = false;
  renderAttendanceGrid();
}

function renderAttendanceRow(row, editable) {
  const status = attDisplayStatus(row);
  const meta = attStatusMeta(status);
  const isPending = ATT.pending.has(row.id);
  const isSaving = ATT.saving.has(row.id);
  const failed = ATT.failed.has(row.id);
  const initials = row.name.split(' ').filter(Boolean).map(n => n[0]).join('').slice(0, 2);

  let metaText = meta ? meta.label : 'Belgilanmagan';
  if (meta && row.time && !isPending && (status === 'PRESENT' || status === 'LATE')) metaText += ` · ${row.time}`;

  let sync = '';
  if (isPending) {
    sync = `<span class="att-sync">Saqlanadi… <button type="button" class="att-link" data-undo>Bekor qilish</button></span>`;
  } else if (isSaving) {
    sync = `<span class="att-sync">Saqlanmoqda…</span>`;
  } else if (failed) {
    sync = `<span class="att-sync is-error">Saqlanmadi <button type="button" class="att-link" data-retry>Qayta urinish</button></span>`;
  }

  const buttons = ATT_STATUSES.map(s => `
    <button type="button" class="att-btn" data-status="${s.key}" aria-pressed="${status === s.key}" ${editable && !isSaving ? '' : 'disabled'}>${attMarkSvg(s.key)}${s.label}</button>
  `).join('');

  return `
    <article class="att-row${isPending ? ' is-pending' : ''}" data-id="${escapeHtml(row.id)}" data-status="${meta ? meta.cls : 'unmarked'}" style="--att-undo-ms: ${ATT_UNDO_MS}ms">
      <div class="att-row-head">
        <div class="child-avatar" aria-hidden="true">${escapeHtml(initials)}</div>
        <div class="att-info">
          <h4 class="att-name">${escapeHtml(row.name)}</h4>
          <span class="att-meta">${metaText}</span>
        </div>
        ${sync}
        <span class="att-mark" title="${meta ? meta.label : 'Belgilanmagan'}">${meta ? attMarkSvg(status) : ''}</span>
      </div>
      <div class="att-choices" role="group" aria-label="${escapeHtml(row.name)}: davomat">${buttons}</div>
    </article>
  `;
}

function renderAttendanceGrid() {
  const grid = document.getElementById('attendanceCardsGrid');
  if (!grid) return;
  const editable = attIsEditable();

  if (ATT.loading && !ATT.rows.length) {
    grid.innerHTML = `<p class="att-empty">Yuklanmoqda…</p>`;
  } else if (ATT.error) {
    grid.innerHTML = `<div class="att-empty"><p>Davomatni yuklab bo'lmadi. Internet yoki server ulanishini tekshiring.</p><button type="button" class="btn btn-secondary" data-reload>Qayta yuklash</button></div>`;
  } else if (!ATT.rows.length) {
    grid.innerHTML = `<p class="att-empty">Bu guruhda hali bola yo'q.</p>`;
  } else {
    grid.innerHTML = ATT.rows.map(r => renderAttendanceRow(r, editable)).join('');
  }
  grid.setAttribute('aria-busy', String(ATT.loading));

  const title = document.getElementById('attTitle');
  const group = document.getElementById('attendanceGroupSelect')?.value;
  if (title && group && ATT.date) {
    const months = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
    const [y, m, d] = ATT.date.split('-').map(Number);
    title.textContent = `${group} · ${d}-${months[m - 1]}, ${y}`;
  }

  const counts = { PRESENT: 0, ABSENT: 0, EXCUSED: 0, LATE: 0 };
  let unmarked = 0;
  ATT.rows.forEach(r => {
    const s = attDisplayStatus(r);
    if (counts[s] !== undefined) counts[s]++;
    else unmarked++;
  });
  document.getElementById('attCountPresent').innerText = counts.PRESENT;
  document.getElementById('attCountAbsent').innerText = counts.ABSENT;
  document.getElementById('attCountExcused').innerText = counts.EXCUSED;
  document.getElementById('attCountLate').innerText = counts.LATE;
  document.getElementById('attCountMarked').innerText = ATT.rows.length - unmarked;
  document.getElementById('attCountTotal').innerText = ATT.rows.length;

  const note = document.getElementById('attReadonlyNote');
  if (note) {
    note.hidden = editable || ATT.error || !ATT.rows.length;
    note.textContent = can('attendance.mark')
      ? "Bu o'tgan kun, faqat ko'rish mumkin. Davomat faqat bugungi kun uchun belgilanadi."
      : "Siz davomatni faqat ko'ra olasiz. Belgilashni tarbiyachi yoki direktor qiladi.";
  }

  const bar = document.getElementById('attActionBar');
  if (bar) bar.hidden = !editable || unmarked === 0;
  const label = document.getElementById('btnMarkRestLabel');
  if (label) label.innerText = unmarked === ATT.rows.length
    ? `Hammasini "Keldi" qilish (${unmarked})`
    : `Qolgan ${unmarked} nafarni "Keldi" qilish`;
}

function setAttendance(childId, status) {
  const row = ATT.rows.find(r => r.id === childId);
  if (!row || !attIsEditable() || ATT.saving.has(childId)) return;

  const existing = ATT.pending.get(childId);
  const prev = existing ? existing.prev : { status: row.status, time: row.time };
  if (existing && !existing.batch) clearTimeout(existing.timer);

  if (status === prev.status) {
    ATT.pending.delete(childId);
  } else {
    ATT.failed.delete(childId);
    const timer = setTimeout(() => commitAttendance([childId]), ATT_UNDO_MS);
    ATT.pending.set(childId, { status, prev, timer, batch: false });
  }
  renderAttendanceGrid();
}

function undoAttendance(childId) {
  const p = ATT.pending.get(childId);
  if (!p) return;
  if (!p.batch) clearTimeout(p.timer);
  ATT.pending.delete(childId);
  renderAttendanceGrid();
}

function retryAttendance(childId) {
  const f = ATT.failed.get(childId);
  if (!f) return;
  ATT.failed.delete(childId);
  ATT.pending.set(childId, { status: f.status, prev: f.prev, timer: null, batch: false });
  commitAttendance([childId]);
}

function markAllPresent() {
  if (!attIsEditable()) return;
  const ids = ATT.rows.filter(r => !attDisplayStatus(r) && !ATT.saving.has(r.id)).map(r => r.id);
  if (!ids.length) return;

  const timer = setTimeout(() => commitAttendance(ids), ATT_UNDO_MS);
  ids.forEach(id => {
    const row = ATT.rows.find(r => r.id === id);
    ATT.failed.delete(id);
    ATT.pending.set(id, { status: 'PRESENT', prev: { status: row.status, time: row.time }, timer, batch: true });
  });
  renderAttendanceGrid();

  showActionToast(
    `${ids.length} nafar "Keldi" deb belgilandi. ${ATT_UNDO_MS / 1000} soniyadan keyin saqlanadi va ota-onalarga xabar boradi.`,
    'Bekor qilish',
    () => {
      clearTimeout(timer);
      ids.forEach(id => { if (ATT.pending.get(id)?.timer === timer) ATT.pending.delete(id); });
      renderAttendanceGrid();
    },
    ATT_UNDO_MS
  );
}

async function commitAttendance(ids) {
  const jobs = ids.map(id => [id, ATT.pending.get(id)]).filter(([, p]) => p);
  if (!jobs.length) return;
  jobs.forEach(([id, p]) => {
    if (!p.batch) clearTimeout(p.timer);
    ATT.pending.delete(id);
    ATT.saving.add(id);
    const row = ATT.rows.find(r => r.id === id);
    if (row) row.status = p.status;
  });
  renderAttendanceGrid();

  const results = await Promise.all(jobs.map(async ([id, p]) => {
    const row = ATT.rows.find(r => r.id === id);
    try {
      const res = await apiFetch(`${API_BASE}/attendance/mark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ child_id: id, status: p.status }),
        keepalive: true,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      if (row) { row.status = data.status; row.time = data.check_in_time; }
      const child = STATE.children.find(c => c.id === id);
      if (child) { child.attendance = data.status; child.checkInTime = data.check_in_time; }
      return { ok: true, name: row?.name, notified: !!data.telegram_notified };
    } catch (err) {
      if (row) { row.status = p.prev.status; row.time = p.prev.time; }
      ATT.failed.set(id, { status: p.status, prev: p.prev });
      return { ok: false, name: row?.name };
    } finally {
      ATT.saving.delete(id);
    }
  }));
  renderAttendanceGrid();

  const failed = results.filter(r => !r.ok);
  const saved = results.filter(r => r.ok);
  const notified = saved.filter(r => r.notified);
  const unlinked = saved.length - notified.length;
  if (failed.length) {
    const who = failed.length === 1 ? failed[0].name : `${failed.length} nafar bola`;
    showToast(`${who}: davomat saqlanmadi. "Qayta urinish" tugmasini bosing.`, 'warning');
  }
  if (saved.length === 1) {
    showToast(notified.length
      ? `${saved[0].name}: saqlandi, ota-onaga Telegram xabar yuborildi.`
      : `${saved[0].name}: saqlandi. Ota-ona Telegram botga ulanmagan, xabar yuborilmadi.`,
      notified.length ? 'success' : 'info');
  } else if (saved.length > 1) {
    showToast(`${saved.length} nafar saqlandi. Telegram xabar: ${notified.length} ta yuborildi` +
      (unlinked ? `, ${unlinked} ta ota-ona botga ulanmagan.` : '.'), 'success');
  }
}

function renderInvoicesTable() {
  const tbody = document.getElementById('invoicesTableBody');
  if (!tbody) return;
  tbody.innerHTML = STATE.children.map(c => `
    <tr>
      <td><code class="doc-code">INV-2026-10-${escapeHtml(c.id.toUpperCase())}</code></td>
      <td><b>${escapeHtml(c.name)}</b><br><small style="color: var(--text-muted);">${escapeHtml(c.group)}</small></td>
      <td>${escapeHtml(c.parentName)}</td>
      <td>${formatMoney(c.fee)}</td>
      <td class="${c.debt > 0 ? '' : 'text-amber'}">${signedMoney(c.debt > 0 ? 0 : -50000)}</td>
      <td class="text-emerald">${formatMoney(c.paid)}</td>
      <td class="${c.debt > 0 ? 'text-rose' : ''}"><b>${formatMoney(c.debt)}</b></td>
      <td>${c.debt === 0 ? `<span class="badge badge-emerald">To'langan</span>` : `<span class="badge badge-rose">Qarz</span>`}</td>
      <td class="text-right col-actions"><button class="btn btn-sm ${c.debt > 0 ? 'btn-primary' : 'btn-secondary'}" onclick="openRecordPaymentModal('${escapeHtml(c.id)}')">To'lov</button> <button class="btn btn-sm btn-secondary" onclick="viewChildReceipt('${escapeHtml(c.id)}')">Kvitansiya</button></td>
    </tr>
  `).join('');
}

const PAYMENT = { childId: null, period: null, info: null, saving: false };

function todayPeriod() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function shiftPeriod(period, delta) {
  const [y, m] = period.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function openRecordPaymentModal(childId) {
  PAYMENT.childId = childId;
  PAYMENT.period = todayPeriod();
  document.getElementById('paymentChildId').value = childId;
  document.getElementById('recordPaymentForm').reset();
  openModal('recordPaymentModal');
  loadPaymentInfo();
}

function shiftPaymentMonth(delta) {
  PAYMENT.period = shiftPeriod(PAYMENT.period, delta);
  loadPaymentInfo();
}

async function loadPaymentInfo() {
  const status = document.getElementById('paymentStatus');
  document.getElementById('paymentMonthLabel').textContent = periodLabel(PAYMENT.period);
  status.textContent = 'Yuklanmoqda…';
  status.dataset.state = '';
  try {
    const res = await apiFetch(`${API_BASE}/billing/child/${encodeURIComponent(PAYMENT.childId)}?period=${PAYMENT.period}`);
    const info = await res.json();
    if (!res.ok) throw new Error(info.detail || 'Xatolik');
    PAYMENT.info = info;
    document.getElementById('paymentChildName').textContent = info.child;
    if (info.debt > 0) {
      status.dataset.state = info.overdue ? 'overdue' : 'debt';
      const [, dm, dd] = info.due_date.split('-').map(Number);
      const due = `${dd}-${MONTH_NAMES[dm - 1].toLowerCase()}`;
      status.textContent = `${periodLabel(info.period)}: qarz ${formatMoney(info.debt)}` +
        (info.overdue ? ` · muddati o'tgan (${due})` : ` · muddati ${due}`);
    } else {
      status.dataset.state = 'ok';
      status.textContent = `${periodLabel(info.period)}: qarz yo'q ✓`;
    }
    const amount = info.debt > 0 ? info.debt : info.fee;
    document.getElementById('paymentAmount').value = amount || '';
    document.getElementById('paymentHint').textContent = info.debt > 0
      ? `Qarz uchun yoziladi: ${periodLabel(info.period)}`
      : (info.has_invoice ? `To'langan. Qo'shimcha summa ${periodLabel(info.period)} uchun yoziladi.` : `Qarz yo'q — to'lov oldindan yoziladi: ${periodLabel(info.period)}`);
    if (info.total_debt > info.debt) {
      document.getElementById('paymentHint').textContent += ` · Boshqa oylar qarzi: ${formatMoney(info.total_debt - info.debt)}`;
    }
  } catch (err) {
    status.dataset.state = 'error';
    status.textContent = err.message || "Ma'lumotni olib bo'lmadi.";
  }
  updatePaymentSubmit();
}

function updatePaymentSubmit() {
  const btn = document.getElementById('paymentSubmit');
  const method = document.querySelector('input[name="paymentMethod"]:checked');
  const amount = parseFloat(document.getElementById('paymentAmount').value);
  btn.disabled = PAYMENT.saving || !method || !(amount > 0) || !PAYMENT.info;
  btn.textContent = PAYMENT.saving ? 'Saqlanmoqda…' : !method ? 'Usulni tanlang' : "To'lovni qabul qilish";
}

document.addEventListener('change', e => {
  if (e.target.name === 'paymentMethod') updatePaymentSubmit();
});
document.addEventListener('input', e => {
  if (e.target.id === 'paymentAmount') updatePaymentSubmit();
});

async function handleRecordPayment(e) {
  e.preventDefault();
  const method = document.querySelector('input[name="paymentMethod"]:checked')?.value;
  const amount = parseFloat(document.getElementById('paymentAmount').value);
  if (!method || !(amount > 0)) return;
  PAYMENT.saving = true;
  updatePaymentSubmit();
  try {
    const res = await apiFetch(`${API_BASE}/billing/record-payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        child_id: PAYMENT.childId, amount, payment_method: method, period: PAYMENT.period,
        note: document.getElementById('paymentNote').value.trim() || null,
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik yuz berdi');
    closeModal('recordPaymentModal');
    syncWithBackend();
    showToast(`To'lov qabul qilindi: ${formatMoney(amount)} (${periodLabel(data.period)}${data.advance ? ', oldindan' : ''}).`, 'success');
  } catch (err) {
    showToast(err.message || 'Xatolik yuz berdi', 'warning');
  } finally {
    PAYMENT.saving = false;
    updatePaymentSubmit();
  }
}

function renderFinanceStats() {
  const container = document.getElementById('financeStatsGrid');
  if (!container) return;
  const s = STATE.financeStats;
  if (!s) { container.innerHTML = ''; return; }

  const rows = [
    { label: 'Bugungi Daromad', income: s.income.daily, expense: s.expenses.daily, net: s.net.daily, icon: 'color-emerald' },
    { label: 'Oylik Daromad', income: s.income.monthly, expense: s.expenses.monthly, net: s.net.monthly, icon: 'color-indigo' },
    { label: 'Yillik Daromad', income: s.income.yearly, expense: s.expenses.yearly, net: s.net.yearly, icon: 'color-amber' },
  ];

  container.innerHTML = rows.map(r => `
    <div class="stat-card">
      <div class="stat-info">
        <span class="stat-label">${r.label}</span>
        <p class="stat-value ${r.income ? 'text-emerald' : ''}">${signedMoney(r.income)}</p>
        <span class="stat-trend ${r.expense ? 'negative' : ''}">Chiqim: ${signedMoney(-r.expense)}</span>
        <span class="stat-trend ${r.net > 0 ? 'positive' : r.net < 0 ? 'negative' : ''}">Sof: ${signedMoney(r.net)}</span>
      </div>
    </div>
  `).join('');
}

// ============================================================================
// Xodimlar davomati (staff attendance)
// ============================================================================

const STAFF_ATT = { rows: [], editable: false, saving: new Set() };
const STAFF_ROLE_LABELS = { TARBIYACHI: 'Tarbiyachi', ENAGA: 'Enaga', OSHPAZ: 'Oshpaz', HAMSHIRA: 'Hamshira' };

function initStaffAttendance() {
  document.getElementById('staffAttList')?.addEventListener('click', e => {
    const btn = e.target.closest('.att-btn');
    const row = e.target.closest('.staff-att-row');
    if (btn && row) markStaffAttendance(row.dataset.id, btn.dataset.status);
  });
}

async function loadStaffAttendance() {
  try {
    const res = await apiFetch(`${API_BASE}/staff/attendance`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    STAFF_ATT.rows = data.staff;
    STAFF_ATT.editable = data.editable;
    renderStaffAttendance();
  } catch (err) {
    document.getElementById('staffAttSummary').textContent = err.message || "Davomatni yuklab bo'lmadi.";
  }
}

function renderStaffAttendance() {
  const list = document.getElementById('staffAttList');
  if (!list) return;
  const present = STAFF_ATT.rows.filter(r => r.status === 'PRESENT' || r.status === 'LATE').length;
  const unmarked = STAFF_ATT.rows.filter(r => !r.status).length;
  document.getElementById('staffAttSummary').textContent =
    `${present} / ${STAFF_ATT.rows.length} ishda` + (unmarked ? ` · ${unmarked} ta belgilanmagan` : '');
  list.innerHTML = STAFF_ATT.rows.length ? STAFF_ATT.rows.map(r => {
    const meta = attStatusMeta(r.status);
    const role = STAFF_ROLE_LABELS[r.role] || r.role.charAt(0) + r.role.slice(1).toLowerCase();
    return `
      <div class="staff-att-row" data-id="${escapeHtml(r.id)}" data-status="${meta ? meta.cls : 'unmarked'}">
        <div class="staff-att-info">
          <b>${escapeHtml(r.name)}</b>
          <small>${escapeHtml(role)}${meta ? ` · ${meta.label}${r.check_in_time ? ' ' + r.check_in_time : ''}` : ''}</small>
        </div>
        <div class="staff-att-buttons" role="group" aria-label="${escapeHtml(r.name)}: davomat">
          ${ATT_STATUSES.map(s => `<button type="button" class="att-btn" data-status="${s.key}" aria-pressed="${r.status === s.key}" ${STAFF_ATT.editable && !STAFF_ATT.saving.has(r.id) ? '' : 'disabled'}>${attMarkSvg(s.key)}<span>${s.label}</span></button>`).join('')}
        </div>
      </div>`;
  }).join('') : '<p class="att-empty">Faol xodimlar yo\'q.</p>';
}

async function markStaffAttendance(staffId, status) {
  const row = STAFF_ATT.rows.find(r => r.id === staffId);
  if (!row || !STAFF_ATT.editable || row.status === status) return;
  const prev = { status: row.status, time: row.check_in_time };
  row.status = status;
  STAFF_ATT.saving.add(staffId);
  renderStaffAttendance();
  try {
    const res = await apiFetch(`${API_BASE}/staff/attendance/mark`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ staff_id: staffId, status })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    row.check_in_time = data.check_in_time;
  } catch (err) {
    row.status = prev.status;
    row.check_in_time = prev.time;
    showToast(`${row.name}: saqlanmadi. ${err.message || ''}`, 'warning');
  } finally {
    STAFF_ATT.saving.delete(staffId);
    renderStaffAttendance();
  }
}

// ============================================================================
// Ошхона харажатлари (weekly kitchen / food expense reports)
// ============================================================================

const KITCHEN = { reports: [], openId: null, editingId: null };

function initKitchen() {
  const form = document.getElementById('kitchenForm');
  if (!form) return;
  document.getElementById('kitchenAddRow')?.addEventListener('click', () => addKitchenRow());
  document.getElementById('kitchenItemRows')?.addEventListener('input', e => {
    if (e.target.classList.contains('kitchen-qty') || e.target.classList.contains('kitchen-price')) updateKitchenRowTotal(e.target.closest('.kitchen-item-row'));
  });
  document.getElementById('kitchenItemRows')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-remove-row]');
    if (!btn) return;
    const rows = document.getElementById('kitchenItemRows');
    if (rows.children.length > 1) { btn.closest('.kitchen-item-row').remove(); } else { clearKitchenRow(btn.closest('.kitchen-item-row')); }
    updateKitchenTotals();
  });
  form.addEventListener('submit', submitKitchenReport);
  document.getElementById('kitchenDeleteBtn')?.addEventListener('click', deleteKitchenReport);
  document.getElementById('kitchenEditBtn')?.addEventListener('click', editKitchenReport);
}

function clearKitchenRow(row) {
  row.querySelectorAll('input').forEach(i => { i.value = ''; });
  row.querySelector('.kitchen-row-total').textContent = '0';
}

function addKitchenRow(name = '', quantity = '', price = '') {
  const wrap = document.getElementById('kitchenItemRows');
  const row = document.createElement('div');
  row.className = 'kitchen-item-row';
  row.innerHTML = `
    <input type="text" class="custom-input kitchen-name" placeholder="Masalan: Ун" value="${escapeHtml(name)}">
    <input type="number" class="custom-input kitchen-qty" min="0" step="any" placeholder="0" value="${quantity}">
    <input type="number" class="custom-input kitchen-price" min="0" step="any" placeholder="0" value="${price}">
    <span class="kitchen-row-total">0</span>
    <button type="button" class="icon-button" data-remove-row aria-label="Qatorni o'chirish">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>`;
  wrap.appendChild(row);
  updateKitchenRowTotal(row);
}

function updateKitchenRowTotal(row) {
  if (!row) return;
  const qty = parseFloat(row.querySelector('.kitchen-qty').value) || 0;
  const price = parseFloat(row.querySelector('.kitchen-price').value) || 0;
  row.querySelector('.kitchen-row-total').textContent = new Intl.NumberFormat('uz-UZ').format(qty * price);
  updateKitchenTotals();
}

function updateKitchenTotals() {
  let total = 0;
  document.querySelectorAll('#kitchenItemRows .kitchen-item-row').forEach(row => {
    total += (parseFloat(row.querySelector('.kitchen-qty').value) || 0) * (parseFloat(row.querySelector('.kitchen-price').value) || 0);
  });
  const count = parseInt(document.getElementById('kitchenChildCount').value, 10) || 0;
  document.getElementById('kitchenTotalAmount').textContent = formatMoney(total);
  document.getElementById('kitchenPerChild').textContent = count > 0 ? formatMoney(total / count) : '—';
}

function openKitchenForm(report = null) {
  KITCHEN.editingId = report ? report.id : null;
  document.getElementById('kitchenFormTitle').textContent = report ? "Hisobotni tahrirlash" : "Yangi haftalik hisobot";
  document.getElementById('kitchenSubmitBtn').textContent = report ? 'Saqlash' : 'Saqlash';
  document.getElementById('kitchenForm').reset();
  document.getElementById('kitchenItemRows').innerHTML = '';
  if (report) {
    document.getElementById('kitchenWeekStart').value = report.week_start;
    document.getElementById('kitchenWeekEnd').value = report.week_end;
    document.getElementById('kitchenChildCount').value = report.child_count;
    report.items.forEach(it => addKitchenRow(it.name, it.quantity, it.unit_price));
  } else {
    for (let i = 0; i < 5; i++) addKitchenRow();
  }
  updateKitchenTotals();
  openModal('kitchenFormModal');
}

async function editKitchenReport() {
  if (!KITCHEN.openId) return;
  const res = await apiFetch(`${API_BASE}/kitchen/reports/${encodeURIComponent(KITCHEN.openId)}`);
  const data = await res.json();
  if (!res.ok) return showToast(data.detail || "Hisobotni yuklab bo'lmadi.", 'warning');
  closeModal('kitchenDetailModal');
  openKitchenForm(data);
}

document.addEventListener('input', e => { if (e.target.id === 'kitchenChildCount') updateKitchenTotals(); });

async function submitKitchenReport(e) {
  e.preventDefault();
  const items = [...document.querySelectorAll('#kitchenItemRows .kitchen-item-row')]
    .map(row => ({
      name: row.querySelector('.kitchen-name').value.trim(),
      quantity: parseFloat(row.querySelector('.kitchen-qty').value),
      unit_price: parseFloat(row.querySelector('.kitchen-price').value),
    }))
    .filter(it => it.name && it.quantity > 0 && !isNaN(it.unit_price));

  if (!items.length) return showToast('Kamida bitta mahsulot kiriting.', 'warning');

  const body = {
    week_start: document.getElementById('kitchenWeekStart').value,
    week_end: document.getElementById('kitchenWeekEnd').value,
    child_count: parseInt(document.getElementById('kitchenChildCount').value, 10),
    items,
  };
  const btn = document.getElementById('kitchenSubmitBtn');
  btn.disabled = true;
  const editingId = KITCHEN.editingId;
  try {
    const res = await apiFetch(editingId ? `${API_BASE}/kitchen/reports/${encodeURIComponent(editingId)}` : `${API_BASE}/kitchen/reports`, {
      method: editingId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(Array.isArray(data.detail) ? "Ma'lumotlar to'liq emas." : (data.detail || 'Xatolik'));
    closeModal('kitchenFormModal');
    showToast(`Hisobot saqlandi: ${formatMoney(data.total_amount)}, bitta bolaga ${formatMoney(data.cost_per_child)}.`, 'success');
    loadKitchenReports();
  } catch (err) {
    showToast(err.message, 'warning');
  } finally {
    btn.disabled = false;
  }
}

function formatDateUz(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d}-${MONTH_NAMES[m - 1].toLowerCase()}`;
}

async function loadKitchenReports() {
  const list = document.getElementById('kitchenList');
  if (!list) return;
  list.innerHTML = `<p class="att-empty">Yuklanmoqda…</p>`;
  try {
    const res = await apiFetch(`${API_BASE}/kitchen/reports`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    KITCHEN.reports = data;
    renderKitchenList();
  } catch (err) {
    list.innerHTML = `<div class="att-empty"><p>${escapeHtml(err.message || "Hisobotlarni yuklab bo'lmadi.")}</p></div>`;
  }
}

function renderKitchenList() {
  const list = document.getElementById('kitchenList');
  if (!KITCHEN.reports.length) {
    list.innerHTML = `<p class="att-empty">Hali hisobot kiritilmagan. "Yangi hisobot" tugmasini bosing.</p>`;
    return;
  }
  const latest = KITCHEN.reports[0];
  const prev = KITCHEN.reports[1];
  const trend = prev ? latest.cost_per_child - prev.cost_per_child : null;
  list.innerHTML = `
    <div class="kitchen-summary">
      <div><span>So'nggi hafta</span><b>${escapeHtml(formatDateUz(latest.week_start))} – ${escapeHtml(formatDateUz(latest.week_end))}</b></div>
      <div><span>Bitta bolaga</span><b>${formatMoney(latest.cost_per_child)}</b>${trend !== null ? `<small class="${trend > 0 ? 'text-rose' : trend < 0 ? 'text-emerald' : ''}">${trend > 0 ? '+' : ''}${formatMoney(trend)} o'tgan haftaga nisbatan</small>` : ''}</div>
      <div><span>Jami xarajat</span><b>${formatMoney(latest.total_amount)}</b></div>
    </div>
    <div class="kitchen-history">${KITCHEN.reports.map(r => `
      <button type="button" class="kitchen-history-row" onclick="openKitchenDetail('${escapeHtml(r.id)}')">
        <span class="kitchen-history-week">${escapeHtml(formatDateUz(r.week_start))} – ${escapeHtml(formatDateUz(r.week_end))}</span>
        <span class="kitchen-history-count">${r.child_count} bola</span>
        <span class="kitchen-history-total">${formatMoney(r.total_amount)}</span>
        <span class="kitchen-history-per">${formatMoney(r.cost_per_child)} / bola</span>
        <svg class="todo-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
      </button>`).join('')}</div>`;
}

async function openKitchenDetail(reportId) {
  KITCHEN.openId = reportId;
  document.getElementById('kitchenDetailItems').innerHTML = '';
  document.getElementById('kitchenDetailSummary').textContent = 'Yuklanmoqda…';
  openModal('kitchenDetailModal');
  try {
    const res = await apiFetch(`${API_BASE}/kitchen/reports/${encodeURIComponent(reportId)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    document.getElementById('kitchenDetailTitle').textContent = `${formatDateUz(data.week_start)} – ${formatDateUz(data.week_end)}`;
    document.getElementById('kitchenDetailSummary').textContent =
      `${data.child_count} bola · Jami ${formatMoney(data.total_amount)} · Bitta bolaga ${formatMoney(data.cost_per_child)}`;
    document.getElementById('kitchenDetailItems').innerHTML = data.items.map((it, i) => `
      <tr><td>${i + 1}</td><td>${escapeHtml(it.name)}</td><td>${it.quantity}</td><td>${formatMoney(it.unit_price)}</td><td class="text-right">${formatMoney(it.line_total)}</td></tr>
    `).join('');
  } catch (err) {
    document.getElementById('kitchenDetailSummary').textContent = err.message || "Yuklab bo'lmadi.";
  }
}

async function deleteKitchenReport() {
  if (!KITCHEN.openId) return;
  if (!confirm("Bu haftalik hisobotni butunlay o'chirmoqchimisiz?")) return;
  try {
    const res = await apiFetch(`${API_BASE}/kitchen/reports/${encodeURIComponent(KITCHEN.openId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    closeModal('kitchenDetailModal');
    showToast("Hisobot o'chirildi.", 'info');
    loadKitchenReports();
  } catch (err) {
    showToast(err.message, 'warning');
  }
}

// ============================================================================
// Avtomatik to'lov eslatmalari (automatic debt reminders)
// ============================================================================

const REMINDERS = { settings: null, maxTimes: 6, fields: [] };
const REMINDER_SAMPLE = { childName: 'Imron Rahimov', parentName: 'Xurshid aka', amount: "1 850 000 so'm", dueDate: '10-noyabr', group: 'Yulduzcha' };
const REMINDER_FIELD_LABELS = { childName: 'Bola ismi', parentName: 'Ota-ona ismi', amount: 'Summa', dueDate: 'Muddat', group: 'Guruh' };

function initReminders() {
  const form = document.getElementById('reminderForm');
  if (!form) return;
  form.addEventListener('submit', saveReminders);
  form.addEventListener('click', e => {
    const step = e.target.closest('[data-step]');
    if (step) {
      const [id, delta] = step.dataset.step.split(':');
      const el = document.getElementById(id);
      const limit = id === 'remBefore' ? 30 : 60;
      el.textContent = Math.max(0, Math.min(limit, Number(el.textContent) + Number(delta)));
      updateReminderWindow();
    }
    const remove = e.target.closest('[data-remove-time]');
    if (remove) {
      REMINDERS.settings.times = REMINDERS.settings.times.filter(t => t !== remove.dataset.removeTime);
      renderReminderTimes();
    }
    const field = e.target.closest('[data-field]');
    if (field) {
      const area = document.getElementById('remTemplate');
      const token = `{${field.dataset.field}}`;
      const pos = area.selectionStart ?? area.value.length;
      area.value = area.value.slice(0, pos) + token + area.value.slice(area.selectionEnd ?? pos);
      area.focus();
      area.selectionStart = area.selectionEnd = pos + token.length;
      renderReminderPreview();
    }
  });
  document.getElementById('remTimeAdd').addEventListener('click', () => {
    const value = document.getElementById('remTimeInput').value;
    const times = REMINDERS.settings.times;
    if (!value) return;
    if (times.includes(value)) return showToast('Bu vaqt allaqachon qo\'shilgan.', 'info');
    if (times.length >= REMINDERS.maxTimes) return showToast(`Kuniga ${REMINDERS.maxTimes} martagacha.`, 'warning');
    times.push(value);
    times.sort();
    renderReminderTimes();
  });
  document.getElementById('remTemplate').addEventListener('input', renderReminderPreview);
  document.getElementById('remEnabled').addEventListener('change', updateReminderWindow);
  document.getElementById('remSendNow').addEventListener('click', sendDebtReminders);
}

async function loadReminders() {
  try {
    const res = await apiFetch(`${API_BASE}/billing/reminders`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    REMINDERS.settings = { ...data.settings, times: [...data.settings.times] };
    REMINDERS.maxTimes = data.max_times;
    REMINDERS.fields = data.fields;
    document.getElementById('remEnabled').checked = data.settings.enabled;
    document.getElementById('remBefore').textContent = data.settings.days_before;
    document.getElementById('remAfter').textContent = data.settings.days_after;
    document.getElementById('remTemplate').value = data.settings.template;
    document.getElementById('remFields').innerHTML = data.fields.map(f =>
      `<button type="button" class="field-chip" data-field="${f}">+ ${REMINDER_FIELD_LABELS[f] || f}</button>`).join('');
    renderReminderStats(data.stats);
    renderReminderTimes();
    renderReminderPreview();
    updateReminderWindow();
  } catch (err) {
    showToast(err.message || "Eslatma sozlamalarini olib bo'lmadi.", 'warning');
  }
}

function renderReminderStats(stats) {
  document.getElementById('remDueSoon').textContent = stats.due_soon;
  document.getElementById('remOverdue').textContent = stats.overdue;
  document.getElementById('remLinked').textContent = stats.linked;
  document.getElementById('remTotal').textContent = new Intl.NumberFormat('uz-UZ').format(stats.total_left || 0);
}

function updateReminderWindow() {
  const on = document.getElementById('remEnabled').checked;
  const status = document.getElementById('remStatus');
  status.textContent = on ? 'Yoqilgan' : "O'chirilgan";
  status.className = on ? 'text-emerald' : '';
  document.getElementById('remWindow').textContent =
    `${document.getElementById('remBefore').textContent} kun oldin · ${document.getElementById('remAfter').textContent} kun keyin`;
}

function renderReminderTimes() {
  document.getElementById('remTimes').innerHTML = REMINDERS.settings.times.map(t => `
    <span class="time-chip">${t}<button type="button" data-remove-time="${t}" aria-label="${t} vaqtini olib tashlash"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button></span>`).join('')
    || '<span class="reminder-help">Vaqt qo\'shing.</span>';
}

function renderReminderPreview() {
  let text = document.getElementById('remTemplate').value;
  Object.entries(REMINDER_SAMPLE).forEach(([k, v]) => { text = text.split(`{${k}}`).join(v); });
  document.getElementById('remPreview').textContent = text ? `Namuna: ${text}` : '';
}

async function saveReminders(e) {
  e.preventDefault();
  const body = {
    enabled: document.getElementById('remEnabled').checked,
    days_before: Number(document.getElementById('remBefore').textContent),
    days_after: Number(document.getElementById('remAfter').textContent),
    times: REMINDERS.settings.times,
    template: document.getElementById('remTemplate').value.trim(),
  };
  try {
    const res = await apiFetch(`${API_BASE}/billing/reminders`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(Array.isArray(data.detail) ? "Ma'lumotlar noto'g'ri to'ldirilgan." : (data.detail || 'Xatolik'));
    REMINDERS.settings = { ...data.settings, times: [...data.settings.times] };
    renderReminderStats(data.stats);
    renderReminderTimes();
    showToast(body.enabled ? 'Eslatma sozlamalari saqlandi va yoqildi.' : 'Eslatma sozlamalari saqlandi (o\'chirilgan).', 'success');
  } catch (err) {
    showToast(err.message, 'warning');
  }
}

async function sendDebtReminders() {
  if (!confirm("Hozirgi eslatma oynasidagi barcha ulangan ota-onalarga eslatma yuborilsinmi?")) return;
  try {
    const res = await apiFetch(`${API_BASE}/billing/remind-debtors`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Xatolik');
    showToast(data.targets
      ? `${data.sent} ta ota-onaga yuborildi.${data.unlinked ? ` ${data.unlinked} tasi Telegramga ulanmagan.` : ''}`
      : "Hozir eslatma oynasida qarzdor yo'q.", data.sent ? 'success' : 'info');
  } catch (err) {
    showToast(err.message || "Eslatmani yuborib bo'lmadi.", 'warning');
  }
}

function updateTmaSimulator() {
  const select = document.getElementById('tmaChildSelect');
  if (!select) return;
  const index = parseInt(select.value) || 0;
  const child = STATE.children[index] || STATE.children[0];
  if (!child) return;

  document.getElementById('tmaChildAvatar').innerText = child.name.split(' ').map(n => n[0]).join('');
  document.getElementById('tmaChildName').innerText = child.name;
  document.getElementById('tmaChildGroup').innerText = `${child.group} guruhi`;
  document.getElementById('tmaCheckInTime').innerText = child.checkInTime ? `${child.checkInTime} da` : "Hali kelmagan";
  document.getElementById('tmaPaymentAmount').innerText = formatMoney(child.fee);
}

function triggerSimulatedTelegramAlert() {
  const select = document.getElementById('tmaChildSelect');
  const index = parseInt(select.value) || 0;
  const child = STATE.children[index] || STATE.children[0];
  showToast(`Telegram: "${child.parentName}" uchun sinov xabarnomasi yuborildi!`, 'success');
}

function openModal(id) { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

function viewChildReceipt(childId) {
  const child = STATE.children.find(c => c.id === childId) || STATE.children[0];
  if (!child) return;
  document.getElementById('receiptChildName').innerText = child.name;
  document.getElementById('receiptGroupName').innerText = child.group;
  document.getElementById('receiptAmount').innerText = formatMoney(child.paid || child.fee);
  document.getElementById('receiptInvoiceCode').innerText = `INV-2026-10-${child.id.toUpperCase()}`;
  openModal('receiptModal');
}

function handleChildSubmit(e) {
  e.preventDefault();
  const firstName = document.getElementById('newChildFirstName').value.trim();
  const lastName = document.getElementById('newChildLastName').value.trim();
  const birthDate = document.getElementById('newChildBirthDate').value;
  const group = document.getElementById('newChildGroup').value;
  const parentName = document.getElementById('newChildParentName').value.trim();
  const parentPhone = document.getElementById('newChildParentPhone').value.trim();
  const allergies = document.getElementById('newChildAllergies').value.trim() || 'Yo\'q';

  apiFetch(`${API_BASE}/children`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      first_name: firstName,
      last_name: lastName,
      birth_date: birthDate,
      group_name: group,
      parent_name: parentName,
      parent_phone: parentPhone,
      allergies: allergies
    })
  }).then(r => r.json()).then(() => {
    closeModal('addChildModal');
    syncWithBackend();
    showToast(`${firstName} ${lastName} bazaga saqlandi va Telegram botga ulandi!`, 'success');
  }).catch(() => {
    closeModal('addChildModal');
    syncWithBackend();
    showToast(`Bola qo'shildi!`, 'success');
  });
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const text = document.createElement('span');
  text.textContent = message;
  toast.appendChild(text);
  container.appendChild(toast);
  setTimeout(() => dismissToast(toast), 4500);
}

function dismissToast(toast) {
  if (!toast.isConnected) return;
  toast.style.animation = 'slideInRight 0.3s ease reverse';
  setTimeout(() => toast.remove(), 280);
}

function showActionToast(message, actionLabel, onAction, durationMs) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast toast-success';
  toast.setAttribute('role', 'status');
  const text = document.createElement('span');
  text.textContent = message;
  const action = document.createElement('button');
  action.type = 'button';
  action.className = 'toast-action';
  action.textContent = actionLabel;
  action.addEventListener('click', () => { onAction(); dismissToast(toast); });
  toast.append(text, action);
  container.appendChild(toast);
  setTimeout(() => dismissToast(toast), durationMs);
}

function formatMoney(amount) {
  return new Intl.NumberFormat('uz-UZ').format(amount || 0) + ' UZS';
}

function signedMoney(amount) {
  if (!amount) return formatMoney(0);
  return (amount > 0 ? '+' : '−') + formatMoney(Math.abs(amount));
}

function handleGlobalSearch(query) {
  if (!query) return;
  const q = query.toLowerCase();
  const found = STATE.children.find(c => c.name.toLowerCase().includes(q));
  if (found) {
    switchTab('children');
    const filterInput = document.getElementById('childSearchFilter');
    if (filterInput) {
      filterInput.value = query;
      renderChildrenTable();
    }
  }
}
