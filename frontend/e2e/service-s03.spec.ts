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

test("service status shows actual impact and safely handles stale, recovered and failed reads", async ({ page }, info) => {
  await login(page);
  const notice = page.getByTestId("service-status-notice");
  await expect(notice).toContainText(ru["serviceStatus.degraded.title"]);
  await expect(notice).toContainText(ru["serviceStatus.component.exports"]);
  await expect(notice).not.toContainText("CELERY");
  await page.getByTestId("header-notifications-trigger").click();
  await expect(page.getByText("Экспорт: Обработка задерживается. Проверьте состояние сервиса перед повтором действий.", { exact: true })).toHaveCount(1);
  await page.getByTestId("header-notifications-trigger").click();
  await page.screenshot({ path: info.outputPath("service-impact.png"), fullPage: true });

  // Boundary injection only after the real endpoint/fixture proves the banner.
  let state = "unknown";
  await page.route("**/api/service-status/?*", async route => {
    if (state === "error") return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
    return route.fulfill({ json: { status: state, checked_at: new Date().toISOString(), max_age_seconds: 180,
      components: [{ component: "exports", state, last_state: "degraded", episode: 1,
        observed_at: new Date().toISOString(), started_at: new Date().toISOString(),
        recovered_at: state === "healthy" ? new Date().toISOString() : null }] } });
  });
  await notice.getByRole("button", { name: ru["common.refresh"] }).click();
  await expect(notice).toContainText(ru["serviceStatus.unknown.title"]);
  state = "healthy";
  await notice.getByRole("button", { name: ru["common.refresh"] }).click();
  await expect(notice).toContainText(ru["serviceStatus.recovered.title"]);
  state = "error";
  await notice.getByRole("button", { name: ru["common.refresh"] }).click();
  await expect(notice).toContainText(ru["serviceStatus.unknown.title"]);
  await page.unroute("**/api/service-status/?*");
  await notice.getByRole("button", { name: ru["common.refresh"] }).click();
  await expect(notice).toContainText(ru["serviceStatus.degraded.title"]);
  for (const [language, copy] of [["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.reload();
    await expect(notice).toContainText(copy["serviceStatus.degraded.title"]);
    const refresh = notice.getByRole("button", { name: copy["common.refresh"] });
    await refresh.focus();
    await expect(refresh).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`service-impact-${language}.png`), fullPage: true });
  }
});

test("service status keeps operator diagnostics separate from employee impact", async ({ page }) => {
  await login(page, "platform_admin@example.com");
  await page.goto("/platform/operations");
  await expect(page.getByTestId("platform-service-state")).toContainText(ru["serviceStatus.platform.degraded"]);
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
