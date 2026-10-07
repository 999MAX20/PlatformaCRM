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

test("operational summary supplies full visible counts without daily list preloads", async ({ page }) => {
  const requests = watchDailyLists(page);
  const summary = page.waitForResponse(response => new URL(response.url()).pathname === "/api/work-queues/" && response.request().method() === "GET");
  await login(page, "business_owner@example.com");
  const response = await summary;
  expect(response.ok()).toBeTruthy();
  const metrics = (await response.json()).summary;
  for (const key of ["today_appointments", "today_confirmations", "waiting_conversations", "overdue_tasks"]) {
    await expect(page.getByTestId(`dashboard-metric-${key}`).locator(".tabular-nums")).toHaveText(String(metrics[key]));
  }
  expect(requests).toEqual([]);
});

test("financial failure preserves operational data and never falls back to list lengths", async ({ page }) => {
  const requests = watchDailyLists(page);
  await page.route("**/api/analytics/owner-dashboard/**", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await login(page, "business_owner@example.com");
  await expect(page.getByTestId("dashboard-finance").getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("dashboard-metric-today_appointments")).toBeVisible();
  expect(requests).toEqual([]);
  await page.unroute("**/api/analytics/owner-dashboard/**");
  await page.getByTestId("dashboard-finance").getByRole("button").click();
  await expect(page.getByTestId("dashboard-finance").getByRole("alert")).toHaveCount(0);
});

test("manager uses scoped operational data without broad daily list preloads", async ({ page }) => {
  const requests = watchDailyLists(page);
  await login(page, "business_manager@example.com");
  await expect(page.getByTestId("dashboard-operations")).toBeVisible();
  expect(requests).toEqual([]);
  await expect(page.getByTestId("dashboard-finance")).toHaveCount(0);
});

test("denied operational data is not displayed as zero or all clear", async ({ page }) => {
  await page.route(/\/api\/work-queues\/(?:\?.*)?$/, route => route.fulfill({
    status: 403, json: { detail: "Permission denied", code: "permission_denied" },
  }));
  await login(page, "business_owner@example.com");
  await expect(page.getByTestId("dashboard-priority-error")).toBeVisible();
  await expect(page.getByTestId("dashboard-operations")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-priority-error").getByRole("button")).toHaveCount(0);
});
