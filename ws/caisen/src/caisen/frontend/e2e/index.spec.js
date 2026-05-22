import { test, expect } from '@playwright/test';

test.describe('Index Page', () => {
  test('should display title and hero section', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Caisen/);
    await expect(page.locator('h1')).toContainText('Caisen 回测可视化');
  });

  test('should load runs list', async ({ page }) => {
    await page.goto('/');
    // Wait for either loading state or content
    await page.waitForSelector('.loading-state, .cards-grid, .empty-state');
  });

  test('should have quick actions', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.quick-actions')).toBeVisible();
    await expect(page.locator('button:has-text("刷新列表")')).toBeVisible();
  });
});
