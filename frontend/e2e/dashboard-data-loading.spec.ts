import { expect, test, type Page } from "@playwright/test";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated seeded accounts");
  test.setTimeout(60_000);
});

const dailyLists = ["/api/leads/", "/api/appointments/", "/api/tasks/"];

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("dashboard-workspace-ready")).toBeVisible({ timeout: 30_000 });
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

test("attention groups use complete server counts and open the matching record queue", async ({ page }) => {
  await page.route(/\/api\/work-queues\/(?:\?.*)?$/, async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.summary.pending_results = 31;
    data.summary.overdue_tasks = 17;
    await route.fulfill({ response, json: data });
  });
  await login(page, "business_owner@example.com");
  await expect(page.getByTestId("dashboard-group-pending_results").locator(".tabular-nums")).toHaveText("31");
  await expect(page.getByTestId("dashboard-group-overdue_tasks").locator(".tabular-nums")).toHaveText("17");
  await expect(page.getByTestId("dashboard-attention-item")).toHaveCount(0);
  await page.getByTestId("dashboard-group-pending_results").getByRole("link").click();
  await expect(page).toHaveURL(/attention=pending_result/);
  await expect(page.getByTestId("dashboard-operations")).toHaveCount(0);
});

test("refresh retains last summary on a temporary error, recovers and hides it on denial", async ({ page }) => {
  await login(page, "business_owner@example.com");
  const metric = page.getByTestId("dashboard-metric-today_appointments").locator(".tabular-nums");
  const value = await metric.innerText();
  const endpoint = /\/api\/work-queues\/(?:\?.*)?$/;
  await page.route(endpoint, route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.getByTestId("dashboard-operations").getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(page.getByTestId("dashboard-operations").getByRole("alert")).toBeVisible();
  await expect(metric).toHaveText(value);
  await page.unroute(endpoint);
  await page.getByTestId("dashboard-operations").getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(page.getByTestId("dashboard-operations").getByRole("alert")).toHaveCount(0);
  await page.route(endpoint, route => route.fulfill({ status: 403, json: { detail: "Permission denied", code: "permission_denied" } }));
  await page.getByTestId("dashboard-operations").getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(page.getByTestId("dashboard-priority-error")).toBeVisible();
  await expect(page.getByTestId("dashboard-metric-today_appointments")).toHaveCount(0);
});

test("dashboard create action opens the existing appointment form", async ({ page }) => {
  await login(page, "business_owner@example.com");
  await page.getByTestId("dashboard-operations").getByRole("link", { name: "Создать запись", exact: true }).click();
  await expect(page).toHaveURL(/create=1/);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("finance distinguishes available zero, stale snapshot and revoked access", async ({ page }) => {
  let state: "available" | "stale" | "denied" = "available";
  await page.route("**/api/analytics/owner-dashboard/**", async route => {
    if (state === "denied") return route.fulfill({ status: 403, json: { detail: "Permission denied", code: "permission_denied" } });
    const response = await route.fetch();
    const data = await response.json();
    data.financial = { ...data.financial, state, reason: state === "stale" ? "sync_overdue" : null,
      receipts: "0.00", refunds: "0.00", net_receipts: "0.00", currency: "KZT" };
    await route.fulfill({ response, json: data });
  });
  await login(page, "business_owner@example.com");
  const finance = page.getByTestId("dashboard-finance");
  await expect(finance.locator("dd")).toHaveCount(3);
  for (const amount of await finance.locator("dd").all()) await expect(amount).toContainText("0");
  await expect(finance.getByText("Нет финансовых данных", { exact: true })).toHaveCount(0);
  state = "stale";
  await page.getByTestId("dashboard-operations").getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(finance.getByTestId("financial-status")).toContainText("Данные не обновлены.");
  await expect(finance.locator("dd")).toHaveCount(3);
  state = "denied";
  await page.getByTestId("dashboard-operations").getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(finance.getByRole("alert")).toBeVisible();
  await expect(finance.locator("dd")).toHaveCount(0);
  await expect(finance.getByRole("button")).toHaveCount(0);
});

test("upcoming preview keeps five unique records and long names fit the viewport", async ({ page }, testInfo) => {
  await page.route(/\/api\/work-queues\/(?:\?.*)?$/, async route => {
    const response = await route.fetch();
    const data = await response.json();
    const rows = Array.from({ length: 6 }, (_, index) => ({
      type: "appointment", id: 9000 + index, title: `Тестовая запись ${index + 1}: проверка длинного имени клиента`,
      status: "confirmed", client_id: null, lead_id: null, service_id: 1, resource_id: null,
      resource_name: "Тестовое рабочее место с длинным названием", start_at: data.generated_at,
      end_at: data.generated_at, href: `/app/appointments/${9000 + index}`,
    }));
    data.queues.upcoming_appointments = [rows[0], rows[0], ...rows.slice(1)];
    data.summary.upcoming_appointments = 6;
    await route.fulfill({ response, json: data });
  });
  await login(page, "business_owner@example.com");
  const rows = page.getByTestId("dashboard-appointment-row");
  await expect(rows).toHaveCount(5);
  await expect(rows.first().getByRole("link")).toHaveAttribute("href", "/app/appointments/9000");
  expect(await rows.evaluateAll(items => new Set(items.map(item => item.getAttribute("data-appointment-id"))).size)).toBe(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await rows.first().getByRole("link").focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  await expect(rows.first().getByRole("link")).toBeFocused();
  await page.screenshot({ path: testInfo.outputPath("dashboard-filled-fixture.png"), fullPage: true });
  for (const language of ["kk", "en"]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.reload();
    await expect(rows).toHaveCount(5, { timeout: 30_000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await expect(page.locator("main")).not.toContainText(/dashboard\.[a-zA-Z]|M11/);
    await page.screenshot({ path: testInfo.outputPath(`dashboard-filled-${language}-fixture.png`), fullPage: true });
  }
});
