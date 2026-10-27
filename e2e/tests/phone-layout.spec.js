const { test, expect } = require('@playwright/test');
const { loginAs } = require('../helpers');

// Regression test for a real bug: on phone widths, CSS Grid item rows in the
// kitchen-report form overflowed past the modal (inputs have an intrinsic
// minimum width that doesn't shrink below ~170-220px unless min-width: 0 is
// set). The page-level scrollWidth check that was tried manually missed it
// because the overflow was clipped inside the modal, not the whole page —
// so this checks the modal's own box, not document.documentElement.
test.use({ viewport: { width: 375, height: 800 } });

test('kitchen report form has no horizontal overflow on a phone-width screen', async ({ page }) => {
  await loginAs(page, 'accountant');

  // At phone width the sidebar is an off-canvas drawer, opened by #menuToggle.
  await page.locator('#menuToggle').click();
  await page.locator('.nav-item[data-tab="kitchen"]').click();
  await page.locator('[onclick="openKitchenForm()"]').click();
  await expect(page.locator('#kitchenFormModal')).toBeVisible();

  const modalBox = page.locator('#kitchenFormModal .modal-box');
  const overflow = await modalBox.evaluate((el) => el.scrollWidth - el.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);

  const itemRow = page.locator('#kitchenItemRows .kitchen-item-row').first();
  const rowBox = await itemRow.boundingBox();
  const viewportWidth = page.viewportSize().width;
  expect(rowBox.x + rowBox.width).toBeLessThanOrEqual(viewportWidth + 1);
});
