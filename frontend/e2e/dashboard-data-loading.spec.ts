import { expect, test, type Page } from "@playwright/test";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated seeded accounts");
});

const dailyLists = ["/api/leads/", "/api/appointments/", "/api/tasks/"];

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("dashboard-workspace-ready")).toBeVisible();
}

function watchDailyLists(page: Page) {
  const requests: string[] = [];
  page.on("request", request => {
    const path = new URL(request.url()).pathname;
    if (request.method() === "GET" && dailyLists.includes(path)) requests.push(path);
  });
  return requests;
}

test("owner summary supplies visible counts without daily list preloads", async ({ page }) => {
  const requests = watchDailyLists(page);
  const summary = page.waitForResponse(response => new URL(response.url()).pathname === "/api/analytics/owner-dashboard/" && response.request().method() === "GET");
  await login(page, "business_owner@example.com");
  const response = await summary;
  expect(response.ok()).toBeTruthy();
  const metrics = await response.json();
  const leadMetric = page.getByTestId("dashboard-workspace-ready").locator('a[href="/app/leads"]').filter({ hasText: "Новые лиды" });
  await expect(leadMetric.locator(".tabular-nums")).toHaveText(String(metrics.new_leads));
  const appointmentMetric = page.getByTestId("dashboard-workspace-ready").locator('a[href="/app/calendar"]').filter({ hasText: "Записи сегодня" });
  await expect(appointmentMetric.locator(".tabular-nums")).toHaveText(String(metrics.appointments_today));
  expect(requests).toEqual([]);
});

test("owner summary failure still loads permitted daily lists and shows fallback", async ({ page }) => {
  const requests = watchDailyLists(page);
  await page.route("**/api/analytics/owner-dashboard/**", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  const lists = dailyLists.map(path => page.waitForResponse(response => new URL(response.url()).pathname === path && response.request().method() === "GET"));
  await login(page, "business_owner@example.com");
  const responses = await Promise.all(lists);
  for (const response of responses) expect(response.ok()).toBeTruthy();
  expect(requests.sort()).toEqual([...dailyLists].sort());
  const leadsPayload = await responses[0].json();
  const pending = (Array.isArray(leadsPayload) ? leadsPayload : leadsPayload.results).filter((lead: { status: string }) => ["new", "contacted", "in_progress"].includes(lead.status));
  const leadMetric = page.getByTestId("dashboard-workspace-ready").locator('a[href="/app/leads"]').filter({ hasText: "Новые лиды" });
  await expect(leadMetric.locator(".tabular-nums")).toHaveText(String(pending.length));
});

test("manager workspace retains the daily entity lists", async ({ page }) => {
  const requests = watchDailyLists(page);
  await login(page, "business_manager@example.com");
  expect(requests.sort()).toEqual([...dailyLists].sort());
  await expect(page.getByTestId("role-daily-metrics")).toBeVisible();
});
