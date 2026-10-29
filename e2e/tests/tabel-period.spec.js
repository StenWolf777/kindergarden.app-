const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

const dayHeaders = (page) => page.locator('#tabelHeaderRow th').filter({ hasText: /^\d+$/ });

test('accountant can browse attendance sheet by year and month', async ({ page }) => {
  await loginAs(page, 'accountant');
  await page.locator('.nav-item[data-tab="tabel"]').click();

  const year = page.locator('#tabelYearSelect');
  const month = page.locator('#tabelMonthSelect');
  await expect(year).toHaveValue(String(new Date().getFullYear()));

  await month.selectOption('2');
  await expect(page.locator('#tabelPeriodLabel')).toContainText(await year.inputValue());
  const febDays = new Date(Number(await year.inputValue()), 2, 0).getDate();
  await expect(dayHeaders(page)).toHaveCount(febDays);

  await page.getByRole('button', { name: /Oldingi/ }).click();
  await expect(month).toHaveValue('1');
  await expect(dayHeaders(page)).toHaveCount(31);

  await page.getByRole('button', { name: /Oldingi/ }).click();
  await expect(month).toHaveValue('12');
  await expect(year).toHaveValue(String(new Date().getFullYear() - 1));
  // Nothing was marked last December: no invented marks, just blank days.
  await expect(page.locator('#tabelBodyRows tr').first()).toBeVisible();
  await expect(page.locator('#tabelBodyRows .p-cell, #tabelBodyRows .e-cell, #tabelBodyRows .a-cell')).toHaveCount(0);

  await month.selectOption('ALL');
  await expect(page.locator('#tabelHeaderRow th')).toHaveCount(1 + 12 + 4);
});

test('whole-year view links into a month', async ({ page }) => {
  await loginAs(page, 'accountant');
  await page.locator('.nav-item[data-tab="tabel"]').click();
  await page.locator('#tabelYearSelect').selectOption('2026');
  await page.locator('#tabelMonthSelect').selectOption('ALL');

  const link = page.locator('.tabel-year-link').first();
  await expect(link).toBeVisible();
  await link.click();
  await expect(page.locator('#tabelMonthSelect')).not.toHaveValue('ALL');
  await expect(dayHeaders(page).first()).toBeVisible();
});
