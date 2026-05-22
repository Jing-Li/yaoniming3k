import { test, expect } from '@playwright/test';

test.describe('Report Page', () => {
  test('should display report page', async ({ page }) => {
    await page.goto('/report.html');
    await expect(page.locator('body')).toBeVisible();
  });
});
