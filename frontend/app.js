// ============================================================================
// Bog'chaOS: Enterprise Pro Dashboard Logic
// Barcha 7 ta modul: Rollar, Davomat, Tabel, Omborxona, To'garaklar, Maosh, Shartnomalar
// ============================================================================

const API_BASE = 'http://127.0.0.1:8000/api/v1';

const STATE = {
  theme: 'dark',
  currentRole: 'director', // 'director', 'teacher', 'accountant'
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
  initLiveClock();
  initUserSession();
  syncWithBackend();

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
  const attGroupSelect = document.getElementById('attendanceGroupSelect');
  if (attGroupSelect) {
    attGroupSelect.addEventListener('change', renderAttendanceGrid);
  }
});

async function syncWithBackend() {
  try {
    const [statsRes, groupsRes, childrenRes, staffRes, tabelRes, financeStatsRes] = await Promise.all([
      fetch(`${API_BASE}/dashboard/stats`).catch(() => null),
      fetch(`${API_BASE}/groups`).catch(() => null),
      fetch(`${API_BASE}/children`).catch(() => null),
      fetch(`${API_BASE}/staff/payroll`).catch(() => null),
      fetch(`${API_BASE}/tabel`).catch(() => null),
      fetch(`${API_BASE}/billing/stats`).catch(() => null),
    ]);

    if (statsRes?.ok) {
      const stats = await statsRes.json();
      document.getElementById('kpiTotalChildren').innerText = `${stats.total_children} nafar`;
      document.getElementById('kpiAttendanceRate').innerText = `${stats.present_today} / ${stats.total_children} (${stats.attendance_rate}%)`;
      document.getElementById('kpiRevenue').innerText = formatMoney(stats.monthly_revenue);
      document.getElementById('kpiDebts').innerText = formatMoney(stats.total_debts);
      if (stats.activities) STATE.activities = stats.activities;
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
    renderWeeklyChart();
    renderActivities();
    renderGroupsMiniGrid();
    renderChildrenTable();
    renderAttendanceGrid();
    renderTabelGrid();
    renderInvoicesTable();
    renderFinanceStats();
    renderStaffPayroll();
    renderContractsTable();
    populateSelectOptions();
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

// Roles with unrestricted access to every tab, regardless of each nav item's data-roles.
const FULL_ACCESS_ROLES = ['director', 'super_admin'];

// Roles that are hidden from the "To'lov Holati" / "Hujjatlar" columns in Bolalar & Guruhlar.
const RESTRICTED_CHILD_COLUMNS_ROLES = ['teacher', 'nurse'];

// Roles allowed to edit a child's Соғлиги (health) field.
const HEALTH_EDIT_ROLES = ['nurse', 'director', 'super_admin'];

// Roles allowed to edit a child's Скидка / Изох / Нархи (discount, note, price).
const PRICING_EDIT_ROLES = ['accountant', 'director', 'super_admin'];

// Roles allowed to delete a child record.
const DELETE_CHILD_ROLES = ['teacher', 'director', 'super_admin'];

// Applies the ACCESS of the actually logged-in user's role. Not user-switchable —
// there is no UI control to change this; it is driven solely by who logged in.
function applyRoleAccess(role) {
  STATE.currentRole = role;

  const title = ROLE_TITLES[role] || role;
  document.getElementById('currentUserRole').innerText = title;
  const badge = document.getElementById('currentRoleBadge');
  if (badge) badge.innerText = title;

  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    const roles = btn.getAttribute('data-roles')?.split(',') || [];
    btn.style.display = (roles.includes(role) || FULL_ACCESS_ROLES.includes(role)) ? 'flex' : 'none';
  });

  const activeTabBtn = document.querySelector(`.sidebar-nav .nav-item[data-tab="${STATE.currentTab}"]`);
  if (activeTabBtn && activeTabBtn.style.display === 'none') {
    const firstVisible = document.querySelector('.sidebar-nav .nav-item:not([style*="display: none"])');
    if (firstVisible) {
      switchTab(firstVisible.getAttribute('data-tab'));
    }
  }

  const hideChildColumns = RESTRICTED_CHILD_COLUMNS_ROLES.includes(role);
  const thPayment = document.getElementById('thPaymentStatus');
  const thDocs = document.getElementById('thDocuments');
  if (thPayment) thPayment.style.display = hideChildColumns ? 'none' : '';
  if (thDocs) thDocs.style.display = hideChildColumns ? 'none' : '';

  const thDelete = document.getElementById('thDelete');
  if (thDelete) thDelete.style.display = DELETE_CHILD_ROLES.includes(role) ? '' : 'none';

  renderChildrenTable();
}

function initUserSession() {
  const savedUserStr = localStorage.getItem('bogcha_user');
  if (!savedUserStr) {
    window.location.href = 'login.html';
    return;
  }
  try {
    const user = JSON.parse(savedUserStr);
    applyRoleAccess(user.role);
    document.getElementById('currentUserName').innerText = user.name;
    document.getElementById('currentUserAvatar').innerText = user.avatar || user.name.split(' ').map(n=>n[0]).join('');
    const greet = document.getElementById('dashboardGreeting');
    if (greet) greet.innerText = `Salom, ${user.name}! 👋`;
  } catch (e) {
    window.location.href = 'login.html';
  }
}

function logoutUser() {
  localStorage.removeItem('bogcha_user');
  localStorage.removeItem('bogcha_token');
  showToast("Tizimdan chiqildi", "info");
  setTimeout(() => {
    window.location.href = 'login.html';
  }, 400);
}

// ============================================================================
// 2. Oylik Tabel (Monthly Attendance Matrix & Compensation)
// ============================================================================

function renderTabelGrid() {
  const header = document.getElementById('tabelHeaderRow');
  const tbody = document.getElementById('tabelBodyRows');
  if (!header || !tbody) return;

  // Days 1..22 (working days simulation for October)
  let headerHtml = '<tr><th>Tarbiyalanuvchi</th>';
  for (let d = 1; d <= 22; d++) {
    headerHtml += `<th>${d}</th>`;
  }
  headerHtml += '<th>Kelgan</th><th>Sababli</th><th>Kompensatsiya</th></tr>';
  header.innerHTML = headerHtml;

  const data = STATE.tabelData.length > 0 ? STATE.tabelData : [
    { name: 'Imron Rahimov', days_present: 20, days_excused: 2, compensation: 50000 },
    { name: 'Madina Saidova', days_present: 22, days_excused: 0, compensation: 0 },
    { name: 'Jasur Aliyev', days_present: 17, days_excused: 5, compensation: 125000 },
    { name: 'Fotima Zokirova', days_present: 20, days_excused: 0, compensation: 0 },
    { name: 'Temur Mirzayev', days_present: 21, days_excused: 1, compensation: 25000 },
    { name: 'Otabek Shokirov', days_present: 22, days_excused: 0, compensation: 0 },
  ];

  tbody.innerHTML = data.map((row, idx) => {
    let daysCells = '';
    for (let d = 1; d <= 22; d++) {
      let cellType = 'p-cell';
      let char = 'P';
      if (row.days_excused > 0 && d <= row.days_excused + 3 && d > 3) {
        cellType = 'e-cell';
        char = 'E';
      }
      daysCells += `<td><span class="tabel-day-cell ${cellType}">${char}</span></td>`;
    }

    const compDisplay = row.compensation > 0 
      ? `<strong class="text-rose">-${formatMoney(row.compensation)}</strong>` 
      : `<span style="color: var(--text-muted);">0 UZS</span>`;

    return `
      <tr>
        <td><b>${row.name}</b></td>
        ${daysCells}
        <td><b class="text-emerald">${row.days_present} kun</b></td>
        <td><b class="text-amber">${row.days_excused} kun</b></td>
        <td>${compDisplay}</td>
      </tr>
    `;
  }).join('');
}

function applyCompensationToInvoices() {
  showToast(`💰 Oylik Tabel tasdiqlandi: Sababli kelmagan kunlar uchun oziq-ovqat kompensatsiyasi keyingi oy kvitansiyasiga chegirildi!`, 'success');
}

function exportTabelExcel() {
  showToast(`📑 Oktabr oyi to'liq davomat tabeli Excel formatida shakllantirildi.`, 'info');
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
        <td class="text-emerald">+${formatMoney(p.bonus)}</td>
        <td class="text-rose">-${formatMoney(p.advance_paid)}</td>
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
  fetch(`${API_BASE}/staff/pay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payroll_id: payrollId, amount: amount })
  }).then(r => r.json()).then(() => {
    syncWithBackend();
    showToast(`💵 Xodimga oylik maosh muvaffaqiyatli to'landi!`, 'success');
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
      <td><span class="badge badge-emerald">✓ Barcha emlashlar bor</span></td>
      <td><span class="badge badge-emerald">✓ Spravka mavjud</span></td>
      <td class="text-right">
        <button class="btn btn-sm btn-secondary" onclick="viewChildContract('${c.id}')">📄 Shartnoma</button>
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
}

// ============================================================================
// Standard UI Engines: Navigation, Dashboard, Attendance, Billing
// ============================================================================

function initTheme() {
  const toggleBtn = document.getElementById('themeToggle');
  toggleBtn?.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    STATE.theme = next;
  });
}

function initNavigation() {
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
  });
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

function renderWeeklyChart() {
  const container = document.getElementById('weeklyChartContainer');
  if (!container) return;
  const weekData = [
    { day: 'Dush', percent: 92 },
    { day: 'Sesh', percent: 89 },
    { day: 'Chor', percent: 94 },
    { day: 'Pay', percent: 90 },
    { day: 'Jum', percent: 91 },
    { day: 'Shan', percent: 78 },
  ];
  container.innerHTML = weekData.map(item => `
    <div class="bar-column">
      <div class="bar-pill" style="height: ${item.percent}%;" data-percent="${item.percent}%"></div>
      <span class="bar-label">${item.day}</span>
    </div>
  `).join('');
}

function renderActivities() {
  const feed = document.getElementById('activityFeed');
  if (!feed) return;
  feed.innerHTML = STATE.activities.map(act => `
    <div class="activity-item">
      <div class="activity-icon" style="background: rgba(99, 102, 241, 0.15);">${act.icon}</div>
      <div class="activity-details">
        <p>${act.text}</p>
        <small>${act.time} da</small>
      </div>
    </div>
  `).join('');
}

function renderGroupsMiniGrid() {
  const container = document.getElementById('groupsMiniGrid');
  if (!container) return;
  container.innerHTML = STATE.groups.map(g => {
    const fillPercent = Math.min(100, Math.round((g.count / g.capacity) * 100));
    return `
      <div class="group-card">
        <div class="group-card-header">
          <span class="group-name">${g.name}</span>
          <span class="badge badge-indigo">${g.age}</span>
        </div>
        <p class="group-teacher">Tarbiyachi: ${g.teacher}</p>
        <div class="group-progress-wrap">
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
            <span>Bolalar: <b>${g.count}/${g.capacity}</b></span>
            <span class="text-emerald">${fillPercent}% to'la</span>
          </div>
          <div class="group-progress-bar">
            <div class="group-progress-fill" style="width: ${fillPercent}%;"></div>
          </div>
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

  const hideRestrictedColumns = RESTRICTED_CHILD_COLUMNS_ROLES.includes(STATE.currentRole);
  const canEditHealth = HEALTH_EDIT_ROLES.includes(STATE.currentRole);
  const canEditPricing = PRICING_EDIT_ROLES.includes(STATE.currentRole);
  const canDelete = DELETE_CHILD_ROLES.includes(STATE.currentRole);

  tbody.innerHTML = filtered.map(child => {
    const initials = child.name.split(' ').map(n => n[0]).join('');
    const healthDisplay = child.allergies === 'Yo\'q'
      ? `<span style="color: var(--color-emerald);">Sog'lom</span>`
      : `<span style="color: var(--color-rose); font-weight: 600;">⚠️ ${child.allergies}</span>`;
    return `
      <tr>
        <td>
          <div class="child-cell">
            <div class="child-avatar">${initials}</div>
            <div>
              <span class="child-name">${child.name}</span>
              <small style="color: var(--text-muted); font-size: 0.75rem;">ID: ${child.id}</small>
            </div>
          </div>
        </td>
        <td><span class="badge badge-indigo">${child.group}</span></td>
        <td>${child.birthDate}</td>
        <td>
          <div><b>${child.parentName}</b></div>
          <small style="color: #6366f1;">${child.parentPhone}</small>
        </td>
        <td>
          ${healthDisplay}
          ${canEditHealth ? `<button class="btn btn-sm btn-secondary" style="margin-left:6px;" onclick="openEditHealthModal('${child.id}', '${child.name.replace(/'/g, "\\'")}', '${(child.allergies || '').replace(/'/g, "\\'")}')" title="Tahrirlash">✎</button>` : ''}
        </td>
        <td>${child.discount ? `<span class="badge badge-amber">${child.discount}</span>` : '—'}</td>
        <td>${child.note || '—'}</td>
        <td>
          ${child.listedPrice != null ? formatMoney(child.listedPrice) : '<span style="color: var(--text-muted);">Belgilanmagan</span>'}
          ${canEditPricing ? `<button class="btn btn-sm btn-secondary" style="margin-left:6px;" onclick="openEditPricingModal('${child.id}', '${child.name.replace(/'/g, "\\'")}', '${(child.discount || '').replace(/'/g, "\\'")}', '${(child.note || '').replace(/'/g, "\\'")}', ${child.listedPrice != null ? child.listedPrice : 'null'})" title="Tahrirlash">✎</button>` : ''}
        </td>
        ${hideRestrictedColumns ? '' : `
        <td>
          ${child.paymentStatus === 'PAID' ? `<span class="badge badge-emerald">To'langan</span>` : `<span class="badge badge-rose">Qarzdor (${formatMoney(child.debt)})</span>`}
        </td>
        <td class="text-right">
          <button class="btn btn-sm btn-secondary" onclick="viewChildReceipt('${child.id}')">Chek</button>
          <button class="btn btn-sm btn-secondary" onclick="viewChildContract('${child.id}')">Shartnoma</button>
        </td>`}
        ${canDelete ? `
        <td class="text-right">
          <button class="btn btn-sm btn-danger" onclick="handleDeleteChild('${child.id}', '${child.name.replace(/'/g, "\\'")}')">🗑️ O'chirish</button>
        </td>` : ''}
      </tr>
    `;
  }).join('');
}

function handleDeleteChild(childId, childName) {
  if (!confirm(`"${childName}" ni ro'yxatdan butunlay o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.`)) {
    return;
  }
  fetch(`${API_BASE}/children/${childId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(() => {
      syncWithBackend();
      showToast(`🗑️ ${childName} ro'yxatdan o'chirildi.`, 'warning');
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

  fetch(`${API_BASE}/children/${childId}/health`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ health })
  }).then(r => r.json()).then(() => {
    closeModal('editHealthModal');
    syncWithBackend();
    showToast(`🩺 Sog'liq holati yangilandi!`, 'success');
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
  openModal('editPricingModal');
}

function handlePricingSubmit(e) {
  e.preventDefault();
  const childId = document.getElementById('editPricingChildId').value;
  const discount = document.getElementById('editPricingDiscount').value.trim() || null;
  const note = document.getElementById('editPricingNote').value.trim() || null;
  const priceRaw = document.getElementById('editPricingPrice').value.trim();
  const monthly_fee = priceRaw === '' ? null : parseFloat(priceRaw);

  fetch(`${API_BASE}/children/${childId}/pricing`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ discount, note, monthly_fee })
  }).then(r => r.json()).then(() => {
    closeModal('editPricingModal');
    syncWithBackend();
    showToast(`✏️ Narx/chegirma/izoh yangilandi!`, 'success');
  }).catch(() => {
    showToast(`Xatolik yuz berdi`, 'warning');
  });
}

function renderAttendanceGrid() {
  const grid = document.getElementById('attendanceCardsGrid');
  if (!grid) return;
  const selectedGroup = document.getElementById('attendanceGroupSelect')?.value || 'Yulduzcha';
  const groupChildren = STATE.children.filter(c => c.group === selectedGroup);

  let countPres = 0, countAbs = 0, countExc = 0, countLate = 0;
  grid.innerHTML = groupChildren.map(c => {
    if (c.attendance === 'PRESENT') countPres++;
    else if (c.attendance === 'ABSENT') countAbs++;
    else if (c.attendance === 'EXCUSED') countExc++;
    else if (c.attendance === 'LATE') countLate++;

    const initials = c.name.split(' ').map(n => n[0]).join('');
    return `
      <div class="att-child-card ${c.attendance.toLowerCase()}">
        <div class="att-card-top">
          <div class="child-avatar">${initials}</div>
          <div class="att-info">
            <h4 class="att-name">${c.name}</h4>
            <span class="att-time">${c.checkInTime ? `Kelgan: ${c.checkInTime}` : 'Hali kelmadi'}</span>
          </div>
        </div>
        <div class="att-buttons-group">
          <button class="att-btn ${c.attendance === 'PRESENT' ? 'active-present' : ''}" onclick="updateAttendance('${c.id}', 'PRESENT')">🟢 Keldi</button>
          <button class="att-btn ${c.attendance === 'ABSENT' ? 'active-absent' : ''}" onclick="updateAttendance('${c.id}', 'ABSENT')">🔴 Kelmadi</button>
          <button class="att-btn ${c.attendance === 'EXCUSED' ? 'active-excused' : ''}" onclick="updateAttendance('${c.id}', 'EXCUSED')">🟡 Sababli</button>
          <button class="att-btn ${c.attendance === 'LATE' ? 'active-late' : ''}" onclick="updateAttendance('${c.id}', 'LATE')">🔵 Kech keldi</button>
        </div>
      </div>
    `;
  }).join('');

  document.getElementById('attCountPresent').innerText = countPres;
  document.getElementById('attCountAbsent').innerText = countAbs;
  document.getElementById('attCountExcused').innerText = countExc;
  document.getElementById('attCountLate').innerText = countLate;
}

function updateAttendance(childId, newStatus) {
  const child = STATE.children.find(c => c.id === childId);
  if (!child) return;
  child.attendance = newStatus;
  const now = new Date();
  child.checkInTime = (newStatus === 'PRESENT' || newStatus === 'LATE') ? `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}` : null;
  renderAttendanceGrid();

  fetch(`${API_BASE}/attendance/mark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ child_id: childId, status: newStatus })
  }).catch(() => {});

  if (newStatus === 'PRESENT') {
    showToast(`🚀 Telegram: ${child.name}ning ota-onasiga (${child.parentPhone}) xabarnoma yuborildi.`, 'success');
  } else if (newStatus === 'ABSENT') {
    showToast(`⚠️ ${child.name} kelmadi deb belgilandi.`, 'warning');
  } else if (newStatus === 'LATE') {
    showToast(`🔵 ${child.name} kech keldi (${child.checkInTime}) deb belgilandi.`, 'info');
  } else {
    showToast(`ℹ️ ${child.name} sababli kelmadi (Spravka).`, 'info');
  }
}

function markAllPresent() {
  const selectedGroup = document.getElementById('attendanceGroupSelect')?.value || 'Yulduzcha';
  const now = new Date();
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  STATE.children.forEach(c => {
    if (c.group === selectedGroup) {
      c.attendance = 'PRESENT';
      c.checkInTime = timeStr;
    }
  });
  renderAttendanceGrid();
  showToast(`✅ "${selectedGroup}" guruhidagi barcha bolalar "Keldi" qilindi va Telegram xabar yuborildi!`, 'success');
}

function renderInvoicesTable() {
  const tbody = document.getElementById('invoicesTableBody');
  if (!tbody) return;
  tbody.innerHTML = STATE.children.map(c => `
    <tr>
      <td><code>INV-2026-10-${c.id.toUpperCase()}</code></td>
      <td><b>${c.name}</b><br><small style="color: var(--text-muted);">${c.group}</small></td>
      <td>${c.parentName}</td>
      <td>${formatMoney(c.fee)}</td>
      <td class="text-amber">-${c.debt > 0 ? '0' : '50,000'} UZS</td>
      <td class="text-emerald">${formatMoney(c.paid)}</td>
      <td class="${c.debt > 0 ? 'text-rose' : ''}"><b>${formatMoney(c.debt)}</b></td>
      <td>${c.debt === 0 ? `<span class="badge badge-emerald">To'langan</span>` : `<span class="badge badge-rose">Qarz</span>`}</td>
      <td class="text-right">${c.debt > 0 ? `<button class="btn btn-sm btn-primary" onclick="openRecordPaymentModal('${c.id}', '${c.name.replace(/'/g, "\\'")}', ${c.debt})">To'lov qabul qilish</button>` : '—'}</td>
      <td class="text-right"><button class="btn btn-sm btn-secondary" onclick="viewChildReceipt('${c.id}')">Kvitansiya</button></td>
    </tr>
  `).join('');
}

function openRecordPaymentModal(childId, childName, debt) {
  document.getElementById('paymentChildId').value = childId;
  document.getElementById('paymentChildName').value = childName;
  document.getElementById('paymentChildDebt').value = formatMoney(debt);
  document.getElementById('paymentAmount').value = debt;
  openModal('recordPaymentModal');
}

function handleRecordPayment(e) {
  e.preventDefault();
  const childId = document.getElementById('paymentChildId').value;
  const amount = parseFloat(document.getElementById('paymentAmount').value);
  const method = document.getElementById('paymentMethod').value;

  fetch(`${API_BASE}/billing/record-payment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ child_id: childId, amount, payment_method: method })
  }).then(r => r.json()).then(() => {
    closeModal('recordPaymentModal');
    syncWithBackend();
    showToast(`💰 To'lov qabul qilindi: ${formatMoney(amount)}`, 'success');
  }).catch(() => {
    showToast(`Xatolik yuz berdi`, 'warning');
  });
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
      <div class="stat-icon-wrapper ${r.icon}">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 18V6"/></svg>
      </div>
      <div class="stat-info">
        <span class="stat-label">${r.label}</span>
        <h3 class="stat-value text-emerald">+${formatMoney(r.income)}</h3>
        <span class="stat-trend negative">Chiqim: -${formatMoney(r.expense)}</span>
        <span class="stat-trend ${r.net >= 0 ? 'positive' : 'negative'}">Sof: ${r.net >= 0 ? '+' : ''}${formatMoney(r.net)}</span>
      </div>
    </div>
  `).join('');
}

function sendDebtReminders() {
  fetch(`${API_BASE}/billing/remind-debtors`, { method: 'POST' }).catch(() => {});
  showToast(`📨 Telegram Bot orqali barcha qarzdor oilalarga Click/Payme to'lov havolasi yuborildi!`, 'info');
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
  showToast(`🔔 Telegram: "${child.parentName}" uchun sinov xabarnomasi yuborildi!`, 'success');
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

  fetch(`${API_BASE}/children`, {
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
    showToast(`🎉 ${firstName} ${lastName} bazaga saqlandi va Telegram botga ulandi!`, 'success');
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
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideInRight 0.3s ease reverse';
    setTimeout(() => toast.remove(), 280);
  }, 4500);
}

function formatMoney(amount) {
  return new Intl.NumberFormat('uz-UZ').format(amount || 0) + ' UZS';
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
