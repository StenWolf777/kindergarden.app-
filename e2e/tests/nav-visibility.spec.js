const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

// Mirrors backend/app/security.py's PERMISSIONS for the tabs the sidebar
// actually gates (data-perm on each .nav-item in frontend/index.html). If
// security.py changes, this table must be updated to match — that's the
// point: a drift between the two is exactly what this test should catch.
const ALL_STAFF = ['super_admin', 'director', 'accountant', 'teacher', 'nurse'];
const MANAGEMENT = ['super_admin', 'director'];
const FINANCE = ['super_admin', 'director', 'accountant'];

const TABS = {
  dashboard: FINANCE,
  children: ALL_STAFF,
  attendance: ALL_STAFF,
  photos: [...MANAGEMENT, 'teacher'],
  kitchen: [...MANAGEMENT, 'accountant', 'nurse'],
  tabel: FINANCE,
  billing: FINANCE,
  staff: FINANCE,
  contracts: MANAGEMENT,
  'telegram-simulator': ['super_admin'],
  settings: MANAGEMENT,
};

const ROLES = ['super_admin', 'director', 'accountant', 'teacher', 'nurse'];

for (const role of ROLES) {
  test(`${role} sees exactly the tabs their permissions allow`, async ({ page }) => {
    await loginAs(page, role);

    for (const [tab, allowedRoles] of Object.entries(TABS)) {
      const navItem = page.locator(`.nav-item[data-tab="${tab}"]`);
      const shouldSee = allowedRoles.includes(role);
      if (shouldSee) {
        await expect(navItem).toBeVisible();
      } else {
        await expect(navItem).toBeHidden();
      }
    }
  });
}
