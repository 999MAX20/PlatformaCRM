import { expect, test, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

async function login(page: Page, language: string) {
  await page.setViewportSize({ width: language === "ru" ? 1440 : 390, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByTestId("header-account-link")).toBeVisible();
}
test.afterEach(async ({ page }) => { await page.unrouteAll({ behavior: "wait" }); });

const failure = { status: 503, json: { code: "temporary_service_failure", request_id: "alert-remediation", retryable: true } };

test("connection navigation respects disabled module and preserves reason", async ({ page }) => {
  await page.route("**/api/auth/me/", async route => {
    const response = await route.fetch(); const user = await response.json();
    for (const capability of Object.values(user.capabilities || {}) as Array<{ modules: Record<string, boolean> }>) capability.modules.integrations = false;
    await route.fulfill({ response, json: user });
  });
  await page.route("**/api/analytics/reports/summary/?*", async route => {
    const response = await route.fetch(); const data = await response.json();
    data.financial = { ...data.financial, state: "unavailable", reason: "no_source", source: null };
    await route.fulfill({ response, json: data });
  });
  await login(page, "ru");
  await page.goto("/app/analytics?tab=finance");
  const notice = page.getByTestId("financial-prerequisite");
  await expect(notice).toContainText(ru["finance.reason.no_source"]);
  await expect(notice).toContainText(ru["serviceStatus.askAdmin"]);
  await expect(notice.getByRole("link")).toHaveCount(0);
});

test("resource creation keeps errors in its form and resets them on reopening", async ({ page }) => {
  await login(page, "ru");
  await page.goto("/app/business/resources");
  await page.locator('[data-testid="page-primary-action"]:visible').click();
  const dialog = page.getByTestId("resource-create-modal");
  await dialog.locator('input[name="name"]').fill("Alert creation recovery");
  await page.route("**/api/resources/", route => route.request().method() === "POST" ? route.fulfill(failure) : route.continue());
  await dialog.locator('button[type="submit"]').click();
  if (await dialog.getByTestId("resource-create-schedule").count()) {
    await dialog.locator('input[type="time"]').first().fill("09:30");
    await dialog.locator('button[type="submit"]').click();
  }
  await expect(dialog.getByTestId("inline-fallback")).toBeVisible();
  await expect(page.getByTestId("action-feedback")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.locator('[data-testid="page-primary-action"]:visible').click();
  await expect(dialog.getByTestId("inline-fallback")).toHaveCount(0);
});

test("connection outage remains in the bottom host without moving the page", async ({ page, context }) => {
  await login(page, "ru");
  await page.goto("/app/clients");
  await expect(page.getByTestId("clients-workspace-ready")).toBeVisible();
  const content = page.locator("[data-workspace-content]");
  const top = await content.evaluate(node => node.getBoundingClientRect().top);
  await context.setOffline(true);
  const notice = page.getByTestId("notification-host").getByTestId("connectivity-banner");
  await expect(notice).toBeVisible();
  expect(await content.evaluate(node => node.getBoundingClientRect().top)).toBe(top);
  await context.setOffline(false);
  await expect(notice).toHaveCount(0);
  expect(await content.evaluate(node => node.getBoundingClientRect().top)).toBe(top);
});

test("resource creation with existing branch shows one recoverable form error", async ({ page }) => {
  await login(page, "ru");
  await page.route("**/api/branches/?*", route => route.fulfill({ json: {
    count: 1, next: null, previous: null, results: [{ id: 999, name: "Synthetic branch" }],
  } }));
  await page.goto("/app/business/resources");
  await page.locator('[data-testid="page-primary-action"]:visible').click();
  const dialog = page.getByTestId("resource-create-modal");
  await dialog.locator('input[name="name"]').fill("Alert branch recovery");
  await page.route("**/api/resources/", route => route.request().method() === "POST" ? route.fulfill(failure) : route.continue());
  await dialog.locator('button[type="submit"]').click();
  await expect(dialog.getByTestId("inline-fallback")).toBeVisible();
  await expect(page.getByTestId("action-feedback")).toHaveCount(0);
  await expect(dialog.locator('input[name="name"]')).toHaveValue("Alert branch recovery");
  await expect(dialog.locator('button[type="submit"]')).toBeEnabled();
});

for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`client save error belongs to the dialog and resubmits retained input ${language}`, async ({ page }) => {
    await login(page, language);
    await page.goto("/app/clients");
    await page.getByRole("button", { name: copy["clients.create"], exact: true }).click();
    const form = page.getByTestId("client-action-form");
    const name = `Alert regression ${language} ${Date.now()}`;
    await form.locator('input[name="full_name"]').fill(name);
    let attempts = 0;
    await page.route("**/api/clients/", route => {
      if (route.request().method() !== "POST") return route.continue();
      return ++attempts === 1 ? route.fulfill(failure) : route.continue();
    });
    await page.getByTestId("client-action-submit").click();
    await expect(form.getByTestId("inline-fallback")).toBeVisible();
    await expect(page.getByTestId("inline-fallback")).toHaveCount(1);
    await expect(form.locator('input[name="full_name"]')).toHaveValue(name);
    await expect(page.getByTestId("action-feedback")).toHaveCount(0);
    await page.getByTestId("client-action-submit").click();
    await expect(form).toHaveCount(0);
    expect(attempts).toBe(2);
    await expect(page.getByTestId("inline-fallback")).toHaveCount(0);
  });

  test(`resource error has one channel and save recovers ${language}`, async ({ page }) => {
    await login(page, language);
    await page.goto("/app/business/resources");
    await page.locator('[data-testid="resource-name"]:visible').first().click();
    const dialog = page.getByTestId("resource-edit-modal");
    const input = dialog.locator('input[name="name"]');
    const original = await input.inputValue();
    await input.fill(`${original} ${language}`);
    let attempts = 0;
    await page.route(/\/api\/resources\/\d+\/$/, route => {
      if (route.request().method() !== "PATCH") return route.continue();
      return ++attempts === 1 ? route.fulfill(failure) : route.continue();
    });
    const submit = dialog.locator('button[form="resource-edit-form"]');
    await submit.click();
    await expect(dialog.getByTestId("inline-fallback")).toBeVisible();
    await expect(page.getByTestId("action-feedback")).toHaveCount(0);
    await expect(input).toHaveValue(`${original} ${language}`);
    await submit.click();
    await expect(dialog.getByTestId("inline-fallback")).toHaveCount(0);
    await expect(page.getByTestId("action-feedback")).toBeVisible();
    expect(attempts).toBe(2);
    await input.fill(original);
    await submit.click();
  });

  test(`password mismatch is local and profile confirmation is a toast ${language}`, async ({ page }) => {
    await page.route("**/api/auth/me/", async route => {
      if (route.request().method() !== "GET") return route.continue();
      const response = await route.fetch(); const user = await response.json();
      await route.fulfill({ response, json: { ...user, preferences: { ...user.preferences, language } } });
    });
    await login(page, language);
    await page.goto("/app/account");
    await page.getByRole("button", { name: copy["account.changePassword"], exact: true }).click();
    const dialog = page.getByRole("dialog");
    const inputs = dialog.locator('input[type="password"]');
    await inputs.nth(0).fill("ZaniTest123!");
    await inputs.nth(1).fill("DifferentPassword1!");
    await inputs.nth(2).fill("DifferentPassword2!");
    let requests = 0;
    await page.route("**/api/auth/change-password/", route => { requests++; return route.fulfill({ json: { ok: true } }); });
    await dialog.locator('button[type="submit"]').click();
    await expect(inputs.nth(2)).toHaveAttribute("aria-invalid", "true");
    await expect(inputs.nth(2)).toBeFocused();
    await expect(dialog.getByRole("alert")).toHaveText(copy["account.passwordMismatch"]);
    await expect(dialog.getByTestId("inline-fallback")).toHaveCount(0);
    expect(requests).toBe(0);
    await inputs.nth(2).fill("DifferentPassword1!");
    await expect(inputs.nth(2)).not.toHaveAttribute("aria-invalid", "true");
    await dialog.locator('button[type="submit"]').click();
    await expect(dialog).toHaveCount(0);
    expect(requests).toBe(1);
    const profile = page.locator("#profile");
    const name = profile.locator('input[autocomplete="name"]');
    const original = await name.inputValue();
    await name.fill(`${original} saved`);
    await profile.locator('button[type="submit"]').click();
    await expect(page.getByTestId("action-feedback").filter({ hasText: copy["account.saved"] })).toBeVisible();
    await name.fill(`${original} unsaved`);
    await expect(profile.locator('[role="status"]')).toHaveCount(0);
    await expect(profile.locator('button[type="submit"]')).toBeEnabled();
    await name.fill(original);
    await profile.locator('button[type="submit"]').click();
    await expect(profile.locator('button[type="submit"]')).not.toHaveAttribute("aria-busy", "true");
  });

  test(`service status persists in header without shifting page ${language}`, async ({ page }, info) => {
    let state = "unknown";
    await page.route("**/api/service-status/?*", route => state === "error" ? route.fulfill(failure) : route.fulfill({ json: {
      status: state, checked_at: new Date().toISOString(), max_age_seconds: 180,
      components: [{ component: "exports", state, last_state: "degraded", episode: 1, observed_at: new Date().toISOString(), started_at: null, recovered_at: null }],
    } }));
    await login(page, language);
    await page.goto("/app/clients");
    const workspace = page.locator("[data-workspace-content]");
    const trigger = page.getByTestId("service-status-trigger");
    await expect(trigger).toHaveAttribute("aria-label", copy["serviceStatus.platform.unknown"]);
    await expect(workspace.getByTestId("service-status-notice")).toHaveCount(0);
    const top = await workspace.evaluate(node => node.getBoundingClientRect().top);
    await trigger.focus(); await page.keyboard.press("Enter");
    const notice = page.getByTestId("service-status-notice");
    await expect(notice).toContainText(copy["serviceStatus.unknown.text"]);
    await expect(notice.getByRole("link")).toHaveAttribute("href", "/app/support");
    for (const next of ["degraded", "healthy", "error"]) {
      state = next;
      await notice.getByRole("button", { name: copy["common.refresh"], exact: true }).click();
      await expect(trigger).toHaveAttribute("aria-label", copy[`serviceStatus.platform.${next === "error" ? "unknown" : next}`]);
      expect(await workspace.evaluate(node => node.getBoundingClientRect().top)).toBe(top);
    }
    await page.screenshot({ path: info.outputPath(`service-details-${language}.png`) });
    await page.keyboard.press("Escape");
    await expect(trigger).toBeFocused();
    await expect(trigger).toBeVisible();
    await expect(notice).toHaveCount(0);
    await trigger.click();
    await expect(notice).toBeVisible();
    await notice.getByRole("link").click();
    await expect(page).toHaveURL(/\/app\/support/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });

  test(`bell counters do not turn failed reads into zero ${language}`, async ({ page }) => {
    let unavailable = true;
    await page.route("**/api/notifications/summary/?*", route => unavailable ? route.fulfill(failure) : route.continue());
    await login(page, language);
    await page.getByTestId("header-notifications-trigger").click();
    await expect(page.getByText(copy["serviceStatus.countsUnavailable"], { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: copy["header.markAllRead"] })).toBeDisabled();
    unavailable = false;
    const retry = page.getByTestId("inline-fallback").getByRole("button", { name: copy["common.retry"], exact: true });
    await retry.first().click();
    await expect(retry).toHaveCount(0);
    await expect(page.getByText(copy["serviceStatus.countsUnavailable"], { exact: true })).toHaveCount(0);
  });

  test(`financial prerequisite stays with report and offers relevant navigation ${language}`, async ({ page }, info) => {
    let reason: string | null = "no_source";
    await page.route("**/api/analytics/reports/summary/?*", async route => {
      const response = await route.fetch();
      const data = await response.json();
      data.financial = { ...data.financial, state: reason ? "unavailable" : "available", reason, source: null };
      await route.fulfill({ response, json: data });
    });
    await login(page, language);
    await page.goto("/app/analytics?tab=finance");
    const prerequisite = page.getByTestId("financial-prerequisite");
    await expect(prerequisite).toContainText(copy["finance.reason.no_source"]);
    await expect(prerequisite.getByRole("button")).toHaveCount(0);
    const link = prerequisite.getByRole("link", { name: copy["serviceStatus.openConnections"] });
    await expect(link).toHaveAttribute("href", "/app/integrations");
    await link.focus(); await expect(link).toBeFocused();
    await page.screenshot({ path: info.outputPath(`financial-prerequisite-${language}.png`) });
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/app\/integrations/);
    await page.goto("/app/analytics?tab=finance");
    await expect(prerequisite).toBeVisible();
    reason = "permission_denied";
    await page.getByRole("button", { name: copy["analyticsWorkspace.refresh"], exact: true }).click();
    await expect(prerequisite).toContainText(copy["finance.reason.permission_denied"]);
    await expect(prerequisite.getByRole("link")).toHaveCount(0);
    reason = null;
    await page.getByRole("button", { name: copy["analyticsWorkspace.refresh"], exact: true }).click();
    await expect(prerequisite).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
