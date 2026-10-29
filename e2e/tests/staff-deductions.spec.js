const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

function previousMonth() {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

test('unmarked working days are deducted and can be corrected from the monthly sheet', async ({ page }) => {
  const month = previousMonth();
  await loginAs(page, 'director');

  await page.locator('.nav-item[data-tab="settings"]').click();
  await page.locator('#settingsDeductionStart').fill(`${month}-01`);
  await page.locator('#savePayrollRulesBtn').click();
  await expect(page.locator('.toast-success')).toBeVisible();

  await page.locator('.nav-item[data-tab="staff"]').click();
  await page.locator('#staffMonthInput').fill(month);
  await expect(page.locator('#staffRulesSummary')).toContainText('ish kuni');

  // Nobody was marked last month, so every working day counts as an absence.
  const firstPayRow = page.locator('#staffPayrollTableBody tr').first();
  await expect(firstPayRow.locator('td').nth(5)).toContainText('−');
  await expect(firstPayRow.locator('td').nth(5)).toContainText('kun kelmagan');

  const firstSheetRow = page.locator('#staffSheetBody tr').first();
  const unmarked = firstSheetRow.locator('.staff-sheet-day:has(.u-cell)');
  const before = await unmarked.count();
  expect(before).toBeGreaterThan(0);

  await unmarked.first().click();
  await expect(page.locator('#staffAttPastNote')).toBeVisible();
  await page.locator('#staffAttList .staff-att-row').first().locator('.att-btn[data-status="EXCUSED"]').click();

  await expect(unmarked).toHaveCount(before - 1);
  await expect(firstSheetRow.locator('.e-cell')).toHaveCount(1);
});

test('future days cannot be picked for staff attendance', async ({ page }) => {
  await loginAs(page, 'accountant');
  await page.locator('.nav-item[data-tab="staff"]').click();
  const max = await page.locator('#staffAttDate').getAttribute('max');
  const today = new Date();
  const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  expect(max).toBe(iso);
});
