const { test, expect } = require('@playwright/test');

test('login page renders its form', async ({ page }) => {
  await page.goto('/login.html');
  await expect(page.locator('form input[type="password"]')).toBeVisible();
  await expect(page.locator('form button[type="submit"]')).toBeVisible();
});
