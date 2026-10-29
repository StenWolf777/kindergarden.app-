const { test, expect } = require('@playwright/test');
const { loginAs, API_BASE } = require('../helpers');

function previousMonth() {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return { period: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`, year: d.getFullYear(), index: d.getMonth() };
}

async function recordPayment(page, childId, amount, period) {
  const token = await page.evaluate(() => localStorage.getItem('bogcha_token'));
  const res = await page.request.post(`${API_BASE}/billing/record-payment`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { child_id: childId, amount, payment_method: 'CASH', period },
  });
  expect(res.ok()).toBeTruthy();
}

test('accountant sees monthly revenue, a past month and a child payment history', async ({ page }) => {
  const prev = previousMonth();
  await loginAs(page, 'accountant');
  // A partial payment for last month leaves a debt on that month's bill.
  await recordPayment(page, 'c1', 1000, prev.period);
  await page.reload();
  await page.locator('.nav-item[data-tab="reports"]').click();

  await expect(page.locator('#reportsRevenueBody tr')).toHaveCount(13);
  await page.locator('#reportsYearSelect').selectOption(String(prev.year));
  const monthRow = page.locator('#reportsRevenueBody tr').nth(prev.index);
  await expect(monthRow).toContainText('%');
  await monthRow.getByRole('button').click();
  await expect(page.locator('#reportsPeriodInput')).toHaveValue(prev.period);

  await page.locator('#reportsOnlyDebtors').check();
  const row = page.locator('#reportsPeriodBody tr').first();
  await expect(row.locator('.badge-rose, .badge-amber')).toBeVisible();

  await row.locator('.link-button').click();
  await expect(page.locator('#childHistoryModal')).toHaveClass(/open/);
  await expect(page.locator('#childHistoryBody .history-payments li').first()).toContainText('1');
});

test('an empty past month says so instead of showing nothing', async ({ page }) => {
  await loginAs(page, 'super_admin');
  await page.locator('.nav-item[data-tab="reports"]').click();
  await page.locator('#reportsPeriodInput').fill('2020-01');
  await expect(page.locator('#reportsPeriodBody')).toContainText('hisob yozilmagan');
});
