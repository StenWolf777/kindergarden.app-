const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

// Regression coverage for a real bug found in review: the Settings form's
// save button used to just show a fake success toast with no backend call
// at all (frontend/app.js's saveOrgSettings + backend/app/routes/settings.py
// didn't exist yet). This proves the round trip actually persists, reflects
// in the topbar immediately, and lands in the audit trail.
test('saving organization settings persists, updates the UI, and is audited', async ({ page }) => {
  await loginAs(page, 'director');

  await page.locator('.nav-item[data-tab="settings"]').click();

  const newName = `Test Bogcha ${Date.now()}`;
  await page.locator('#settingsOrgName').fill(newName);
  await page.locator('#settingsOrgPhone').fill('+998901112233');
  await page.locator('#settingsOrgAddress').fill('Toshkent, Yakkasaroy');
  await page.locator('#saveOrgSettingsBtn').click();

  await expect(page.locator('.toast-success')).toBeVisible();
  // The topbar brand name re-renders from a fresh /auth/me call after saving.
  await expect(page.locator('#tenantName')).toHaveText(newName);

  // The audit table (management-only) should now show this change at the top.
  const firstRow = page.locator('#auditLogBody tr').first();
  await expect(firstRow).toContainText(newName);
});

test('a role without settings.manage never sees the save button', async ({ page }) => {
  await loginAs(page, 'accountant');
  // accountant can't even see the Settings tab (settings.view is management-only).
  await expect(page.locator('.nav-item[data-tab="settings"]')).toBeHidden();
});
