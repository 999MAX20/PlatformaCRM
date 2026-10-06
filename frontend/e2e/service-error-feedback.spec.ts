import { expect, test } from "@playwright/test";

test("service edit failure stays in the form once and preserves the draft", async ({ page }) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/business/services");
  const row = page.getByTestId("service-row").filter({ visible: true }).first();
  await row.getByTestId("row-actions-trigger").click();
  await page.getByTestId("action-menu").locator('[data-action-key="open"]').click();
  const modal = page.getByTestId("service-edit-modal");
  const name = modal.locator('input[name="name"]');
  const original = await name.inputValue();
  await name.fill(`${original} draft`);
  await page.route("**/api/services/*/", async route => {
    if (route.request().method() !== "PATCH") return route.continue();
    await route.fulfill({ status: 503, json: { code: "temporary_service_failure", request_id: "service-edit-test", detail: "SQLSTATE private", retryable: true } });
  });
  await modal.locator('button[type="submit"]').click();
  await expect(modal.getByTestId("inline-fallback")).toHaveCount(1);
  await expect(page.getByTestId("action-feedback")).toHaveCount(0);
  await expect(name).toHaveValue(`${original} draft`);
  await expect(modal.locator('button[type="submit"]')).toBeEnabled();
  await expect(modal).not.toContainText("SQLSTATE");
  await modal.locator("summary").click();
  await expect(modal.getByTestId("recovery-details")).toContainText("service-edit-test");
  await page.unroute("**/api/services/*/");
  await modal.locator('button[type="submit"]').click();
  await expect(modal.getByTestId("inline-fallback")).toHaveCount(0);
  await expect(page.getByTestId("action-feedback")).toHaveCount(1);
});
