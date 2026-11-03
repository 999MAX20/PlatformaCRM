import { test, expect, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";

test.beforeEach(() => test.skip(process.env.E2E_CALENDAR_CONSUMERS !== "1", "Use isolated calendar runner"));
async function login(page: Page, platform = false) {
  await page.goto("/login");
  await page.locator('form input[type=email]').fill(platform ? "platform_admin@example.com" : "business_owner@example.com");
  await page.locator('form input[type=password]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type=submit]').click();
  await expect(page).toHaveURL(platform ? /\/platform/ : /\/app/);
}

test("analytics applies range to request and recovers from read failure without losing period", async ({ page }) => {
  await login(page);
  await page.goto("/app/analytics?start=2026-10-01&end=2026-10-31");
  await expect(page.getByTestId("analytics-workspace")).toBeVisible();
  const trigger = page.getByRole("button", { name: ru["analyticsWorkspace.period"], exact: true });
  await trigger.click();
  const panel = page.getByRole("dialog", { name: ru["analyticsWorkspace.period"], exact: true });
  await panel.locator('[data-date="2026-10-05"]').click();
  await panel.locator('[data-date="2026-10-09"]').click();
  const response = page.waitForResponse(r => r.url().includes("/analytics/reports/summary/") && r.url().includes("start=2026-10-05"));
  await panel.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page).toHaveURL(/start=2026-10-05/);
  await expect(page).toHaveURL(/end=2026-10-09/);
  await expect(trigger).toBeFocused();
  await page.route("**/api/analytics/reports/summary/**", route => route.fulfill({ status: 503, json: { detail: "Isolated failure" } }));
  await page.getByLabel(ru["analyticsWorkspace.refresh"], { exact: true }).click();
  await expect(page.getByTestId("inline-fallback")).toBeVisible();
  await expect(page.getByLabel(ru["analyticsWorkspace.refresh"], { exact: true })).toBeEnabled();
  await page.unroute("**/api/analytics/reports/summary/**");
  const recovered = page.waitForResponse(r => r.url().includes("/analytics/reports/summary/") && r.request().method() === "GET");
  await page.getByLabel(ru["analyticsWorkspace.refresh"], { exact: true }).click();
  expect((await recovered).status()).toBe(200);
  await expect(page.getByTestId("inline-fallback")).toHaveCount(0);
  await trigger.click();
  await expect(panel.locator('[data-date="2026-10-05"]')).toHaveAttribute("aria-selected", "true");
  await panel.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
});

test("Records, schedule and client filter calendars remain reachable", async ({ page }) => {
  await login(page);
  await page.goto("/app/calendar?date=2026-11-04");
  await page.getByTestId("calendar-period-picker").click();
  await page.getByTestId("calendar-date-picker").locator('[data-date="2026-11-05"]').click();
  await expect(page).toHaveURL(/date=2026-11-05/);
  await page.goto("/app/appointments?from=2026-11-04&to=2026-11-04");
  await page.locator('[data-focus-return-id="records-period"]').click();
  await page.locator('#records-period-panel [data-date="2026-11-05"]').click();
  await page.locator('#records-period-panel [data-date="2026-11-06"]').click();
  await page.locator("#records-period-panel").getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  await expect(page).toHaveURL(/from=2026-11-05/);
  await page.goto("/app/clients");
  await page.locator('[data-focus-return-id="clients-filters"]').click();
  const filters = page.getByRole("dialog", { name: ru["crmFilters.filters"], exact: true });
  await filters.getByRole("button", { name: new RegExp(`^${ru["crmFilters.created"]}`) }).click();
  const panel = page.getByRole("dialog", { name: ru["crmFilters.created"], exact: true });
  await panel.getByRole("gridcell").nth(10).click();
  await panel.getByRole("gridcell").nth(13).click();
  await panel.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  await filters.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  await expect(page).toHaveURL(/created_from=/);
});

test("task deadline calendar sends chosen date and time through existing API", async ({ page }) => {
  await login(page);
  await page.goto("/app/tasks");
  await page.getByRole("button", { name: ru["taskWorkspace.create"], exact: true }).click();
  const form = page.getByRole("dialog");
  await form.getByLabel(ru["taskWorkspace.name"], { exact: true }).fill("Calendar isolated deadline");
  await form.getByRole("button", { name: ru["calendar.openPicker"].replace("{label}", ru["taskWorkspace.due"]), exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["taskWorkspace.due"], exact: true });
  await panel.getByRole("combobox").first().click();
  await panel.getByRole("option", { name: ru["calendar.month.12"], exact: true }).click();
  await panel.locator('[data-date="2026-12-15"]').click();
  await panel.locator('input[type="time"]').fill("14:35");
  await panel.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  await expect(form.locator('input[type="datetime-local"]').first()).toHaveValue("2026-12-15T14:35");
  const saved = page.waitForResponse(r => r.url().includes("/api/tasks/") && r.request().method() === "POST");
  await form.getByRole("button", { name: ru["taskWorkspace.save"], exact: true }).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const body = await response.json();
  expect(body.due_at).toContain("2026-12-15");
  expect(new Date(body.due_at).toISOString()).toBe("2026-12-15T09:35:00.000Z");
});

test("platform history period updates URL and API without a modal", async ({ page }) => {
  await login(page, true);
  await page.goto("/platform/operations?section=history&date_from=2026-10-01&date_to=2026-10-31");
  await page.getByRole("button", { name: ru["operationsWorkspace.period"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["operationsWorkspace.period"], exact: true });
  await expect(panel).not.toHaveAttribute("aria-modal", "true");
  await panel.locator('[data-date="2026-10-05"]').click();
  await panel.locator('[data-date="2026-10-09"]').click();
  const response = page.waitForResponse(r => r.url().includes("date_from=2026-10-05") && r.url().includes("date_to=2026-10-09"));
  await panel.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page).toHaveURL(/date_from=2026-10-05/);
});
