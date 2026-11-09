import { expect, test, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.E2E_SERVICE_S03 !== "1", "Run scripts/verify_service_s03.py for isolated service observations");
});

async function login(page: Page, email = "business_owner@example.com") {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(email.startsWith("platform") ? /\/platform/ : /\/app/);
}

test("service events show actual impact without the removed header indicator", async ({ page }, info) => {
  await login(page);
  await expect(page.getByTestId("service-status-trigger")).toHaveCount(0);
  await page.getByTestId("header-notifications-trigger").click();
  await expect(page.getByText(ru["notification.service.exports.started"], { exact: true })).toHaveCount(1);
  await page.screenshot({ path: info.outputPath("service-impact.png"), fullPage: true });
  for (const [language, copy] of [["kk", kk], ["en", en]] as const) {
    await page.route("**/api/auth/me/", async route => {
      const response = await route.fetch(); const user = await response.json();
      await route.fulfill({ response, json: { ...user, preferences: { ...user.preferences, language } } });
    });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.reload();
    await page.getByTestId("header-notifications-trigger").click();
    await expect(page.getByText(copy["notification.service.exports.started"], { exact: true })).toHaveCount(1);
    await expect(page.getByTestId("service-status-trigger")).toHaveCount(0);
    await page.unroute("**/api/auth/me/");
  }
});

test("service status keeps operator diagnostics separate from employee impact", async ({ page }) => {
  await login(page, "platform_admin@example.com");
  await page.goto("/platform/operations");
  await expect(page.getByTestId("operations-row").filter({hasText:ru["platform.workspace.service.degraded"]}).first()).toBeVisible();
  await page.getByRole("tab", {name:ru["operationsWorkspace.infrastructure"],exact:true}).click();
  await expect(page.getByRole("heading", { name: ru["serviceStatus.platform.diagnostics"] })).toBeVisible();
  await expect(page.getByTestId("service-status-notice")).toHaveCount(0);
});

test("service connectivity detects an API outage even when the browser stays online", async ({ page }) => {
  let unavailable = true;
  await page.route("**/ready/", route => route.fulfill({ status: unavailable ? 503 : 200, json: { status: unavailable ? "degraded" : "ok" } }));
  await login(page);
  const banner = page.getByTestId("connectivity-banner");
  await expect(banner).toContainText(ru["fallback.connectivity.unavailableText"]);
  await expect(page.getByTestId("header-account-link")).toBeAttached();
  expect(await page.evaluate(() => navigator.onLine)).toBeTruthy();
  unavailable = false;
  await banner.getByRole("button", { name: ru["common.retry"] }).click();
  await expect(banner).toHaveCount(0);
});
