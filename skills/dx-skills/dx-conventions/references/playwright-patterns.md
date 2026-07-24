# Playwright Interaction Testing Patterns

Source: Playwright Skill (lackeyjb) + dx pipeline requirements.

Used by: dx-review Pass 3 (Interaction Verification).

---

## Principles

- Test what a USER does, not implementation details.
- Every test must be runnable with one command.
- Visible browser by default (headless: false) for debugging; CI uses headless.
- Screenshots on failure are mandatory.
- Tests are generated on-the-fly per project — no pre-built script library.

---

## Standard Test Patterns

### Pattern 1: Page Load Verification

Every page MUST pass this. Non-negotiable.

```typescript
test('page loads with correct title and key elements', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/expected-title/i);
  // Key structural elements visible
  await expect(page.locator('header')).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
  // No console errors
  const errors: string[] = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.waitForTimeout(1000);
  expect(errors).toHaveLength(0);
});
```

### Pattern 2: Navigation Flow

For prototypes with routing. Click → URL changes → content changes.

```typescript
test('navigation: home → about → back', async ({ page }) => {
  await page.goto('/');
  // Click nav link
  await page.click('a[href="/about"]');
  await expect(page).toHaveURL(/\/about/);
  await expect(page.locator('h1')).toContainText('About');
  // Navigate back
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
});
```

### Pattern 3: Form Flow

For pages with input forms. Fill → submit → feedback.

```typescript
test('form: fill and submit shows success', async ({ page }) => {
  await page.goto('/contact');
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('textarea[name="message"]', 'Hello');
  await page.click('button[type="submit"]');
  // Success feedback visible
  await expect(page.locator('[role="alert"], .success-message')).toBeVisible();
});

test('form: empty submit shows validation error', async ({ page }) => {
  await page.goto('/contact');
  await page.click('button[type="submit"]');
  await expect(page.locator('.error, [aria-invalid="true"]').first()).toBeVisible();
});
```

### Pattern 4: Responsive Verification

Screenshot at 3 standard viewports. Visual comparison.

```typescript
const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];

for (const vp of viewports) {
  test(`responsive: ${vp.name} (${vp.width}px)`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto('/');
    // No horizontal scroll
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
    // Screenshot for visual record
    await page.screenshot({ path: `screenshots/${vp.name}.png`, fullPage: true });
  });
}
```

### Pattern 5: State Coverage

Empty / Loading / Error / Success states must be reachable.

```typescript
test('empty state: no data shows invitation', async ({ page }) => {
  // Intercept API to return empty
  await page.route('**/api/items', route => route.fulfill({ json: [] }));
  await page.goto('/dashboard');
  await expect(page.locator('.empty-state, [data-testid="empty"]')).toBeVisible();
});

test('error state: API failure shows error UI', async ({ page }) => {
  await page.route('**/api/items', route => route.fulfill({ status: 500 }));
  await page.goto('/dashboard');
  await expect(page.locator('.error-state, [role="alert"]')).toBeVisible();
});

test('loading state: skeleton/spinner during fetch', async ({ page }) => {
  await page.route('**/api/items', async route => {
    await new Promise(r => setTimeout(r, 2000)); // delay
    route.fulfill({ json: [{ id: 1 }] });
  });
  await page.goto('/dashboard');
  await expect(page.locator('.skeleton, .spinner, [aria-busy="true"]')).toBeVisible();
});
```

---

## Test Selection Logic (dx-review Pass 3)

Based on page characteristics, select which patterns to run:

| Page Has... | Run Patterns |
|-------------|-------------|
| Any page | Pattern 1 (Load) + Pattern 4 (Responsive) |
| Navigation/routing | + Pattern 2 (Navigation) |
| Forms/inputs | + Pattern 3 (Form) |
| Data fetching | + Pattern 5 (States) |
| All of above | All patterns |

---

## Execution Rules

1. Generate test file at `dx/review/e2e.spec.ts` (temporary, not committed).
2. Run: `npx playwright test dx/review/e2e.spec.ts --reporter=list`
3. On failure: capture screenshot to `dx/review/screenshots/`
4. Each failed test = one DRIFT item in the report.
5. Pattern 1 failure = P0 (page doesn't load = not deliverable).
6. Pattern 2/3 failure = P0 (broken interaction = not deliverable).
7. Pattern 4 failure (horizontal scroll) = P1.
8. Pattern 5 failure (missing state) = P1.

---

## Cleanup

After dx-review completes:
- Keep screenshots in `dx/review/screenshots/` (part of the report).
- Delete `dx/review/e2e.spec.ts` (generated on-the-fly, not source code).
