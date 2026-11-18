import { expect, test, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

async function login(page: Page, language: string) {
  await page.setViewportSize({ width: language === "ru" ? 1440 : 390, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.route("**/api/auth/me/", async route => {
    const response = await route.fetch(); const user = await response.json();
    await route.fulfill({ response, json: { ...user, preferences: { ...user.preferences, language } } });
  });
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByTestId("header-account-link")).toBeVisible();
}

test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`records real list, filters, empty and read recovery ${language}`, async ({ page }, info) => {
    await login(page, language);
    const loaded = page.waitForResponse(response => response.url().includes("/api/appointments/workspace/") && response.status() === 200);
    await page.goto("/app/appointments?from=2026-12-15&to=2026-12-15");
    expect((await (await loaded).json()).count).toBe(3);
    const recordLinks = page.locator('main a[href^="/app/appointments/"]:visible');
    await expect(recordLinks).toHaveCount(3);
    const filtered = page.waitForResponse(response => response.url().includes("workflow=completed") && response.status() === 200);
    await page.getByRole("combobox", { name: copy["records.pipeline"], exact: true }).click();
    await page.getByRole("option", { name: `${copy["records.completed"]} · 1`, exact: true }).click();
    expect((await (await filtered).json()).count).toBe(1);
    await expect(recordLinks).toHaveCount(1);
    await page.getByRole("textbox", { name: copy["records.search"], exact: true }).fill("NO SUCH FIXTURE CLIENT");
    await expect(page.getByText(copy["records.emptySearch"], { exact: true })).toBeVisible();
    await expect(page.getByTestId("inline-fallback")).toHaveCount(0);

    let failure = 404;
    await page.route("**/api/appointments/workspace/**", route => route.fulfill({ status: failure,
      json: { code: failure === 403 ? "permission_denied" : "request_failed", category: failure === 403 ? "permission" : failure === 503 ? "temporary" : "validation", errors: {}, retryable: false } }));
    await page.goto("/app/appointments?from=2026-12-15&to=2026-12-15");
    const error = page.getByTestId("inline-fallback");
    await expect(error).toContainText(copy["records.loadFailed"]);
    await expect(error).toContainText(copy["records.loadFailedHint"]);
    await expect(error).not.toContainText(copy["fallback.fields.title"]);
    await expect(page.getByTestId("records-empty")).toHaveCount(0);
    for (const status of [503, 400]) {
      failure = status;
      const failed = page.waitForResponse(response => response.url().includes("/api/appointments/workspace/") && response.status() === status);
      await error.getByRole("button", { name: copy["common.retry"], exact: true }).click();
      await failed;
      await expect(error).toContainText(copy[status === 400 ? "records.invalidFilters" : "records.loadFailedHint"]);
    }
    await page.screenshot({ path: info.outputPath(`records-read-error-${language}.png`), fullPage: true });
    failure = 403;
    await error.getByRole("button", { name: copy["common.retry"], exact: true }).click();
    await expect(error).toContainText(copy["fallback.permission.title"]);
    await expect(error).not.toContainText(copy["records.loadFailedHint"]);
    await page.unroute("**/api/appointments/workspace/**");
    await error.getByRole("button", { name: copy["common.retry"], exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(error).toHaveCount(0);
    await expect(recordLinks).toHaveCount(3);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  });

  test(`bell displays actual service start and recovery ${language}`, async ({ page }, info) => {
    await login(page, language);
    await expect(page.getByTestId("service-status-trigger")).toHaveCount(0);
    await page.getByTestId("header-notifications-trigger").click();
    await expect(page.getByText(copy["notification.service.exports.started"], { exact: true })).toBeVisible();
    await expect(page.getByText(copy["notification.service.exports.recovered"], { exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`service-events-${language}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    await page.goto("/app/notifications");
    await expect(page.getByText(copy["notification.service.exports.started"], { exact: true })).toBeVisible();
    await expect(page.getByText(copy["notification.service.exports.recovered"], { exact: true })).toBeVisible();
  });
}
