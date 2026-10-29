const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

// Regression: payStaffSalary used to show a green "saved" toast even when the
// request failed, so a salary could look paid without being recorded.

async function openStaffTab(page) {
  await loginAs(page, 'accountant');
  await page.locator('.nav-item[data-tab="staff"]').click();
}

test('a failed salary payment shows a warning, never a success message', async ({ page }) => {
  await openStaffTab(page);
  await page.route('**/api/v1/staff/pay', (route) => route.abort('connectionfailed'));

  await page.locator('#staffPayrollTableBody .btn-success').first().click();

  await expect(page.locator('.toast-warning')).toBeVisible();
  await expect(page.locator('.toast-success')).toHaveCount(0);
});

test('a server-side rejection shows the server reason as a warning', async ({ page }) => {
  await openStaffTab(page);
  await page.route('**/api/v1/staff/pay', (route) =>
    route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ detail: 'Bu oylik allaqachon to\'langan' }) })
  );

  await page.locator('#staffPayrollTableBody .btn-success').first().click();

  await expect(page.locator('.toast-warning')).toContainText('allaqachon');
  await expect(page.locator('.toast-success')).toHaveCount(0);
});

test('a successful salary payment shows success and marks the row paid', async ({ page }) => {
  await openStaffTab(page);
  const pendingBefore = await page.locator('#staffPayrollTableBody .btn-success').count();

  await page.locator('#staffPayrollTableBody .btn-success').first().click();

  await expect(page.locator('.toast-success')).toBeVisible();
  await expect(page.locator('#staffPayrollTableBody .btn-success')).toHaveCount(pendingBefore - 1);
});
