import { expect, test } from "@playwright/test";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Session mutations require isolated test accounts");
});

test("same-tab account switch uses the new business context", async ({ page }) => {
  const login = async (email: string) => {
    await page.locator('form input[type="email"]').fill(email);
    await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByTestId("header-account-link")).toBeVisible();
  };
  await page.goto("/login");
  await login("business_owner@example.com");
  await page.getByTestId("header-account-link").click();
  const scope = page.getByTestId("account-access-summary");
  await scope.locator("summary").click();
  await expect(scope).toContainText(process.env.E2E_BUSINESS_NAME || "PlatformaCRM E2E Demo");
  await page.evaluate(() => { Reflect.set(window, "sameDocument", true); });
  const logout = page.waitForResponse(r => r.url().endsWith("/api/auth/logout/"));
  await page.getByTestId("merchant-logout").click();
  await logout;
  await expect(page).toHaveURL(/\/login/);
  await login("foreign_owner@example.com");
  expect(await page.evaluate(() => Reflect.get(window, "sameDocument"))).toBe(true);
  await expect(scope).toBeVisible();
  await scope.locator("summary").click();
  await expect(scope).toContainText("PlatformaCRM E2E Foreign Tenant");
});


for (const status of [200, 401]) test(`late ${status} mutation cannot run as the next account`, async ({ page }) => {
  test.setTimeout(60_000);
  const login = async (email: string) => {
    await page.locator('form input[type="email"]').fill(email);
    await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByTestId("header-account-link")).toBeVisible();
  };
  await page.goto("/login");
  await login("business_owner@example.com");
  await page.getByTestId("header-account-link").click();
  await expect(page.getByTestId("merchant-logout")).toBeVisible();
  let release!: () => void;
  let started!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const ready = new Promise<void>(resolve => { started = resolve; });
  const credentials: string[] = [];
  await page.route("**/api/tasks/999999/complete/", async route => {
    credentials.push(route.request().headers().authorization || "");
    if (credentials.length === 1) {
      started();
      await held;
      await route.fulfill({ status, json: { detail: "Delayed old session response" } });
    } else await route.fulfill({ json: { ok: true } });
  });
  await page.evaluate(async () => {
    const modulePath = "/src/api/client.ts";
    const { apiClient } = await import(modulePath);
    Reflect.set(window, "lateMutation", apiClient.post("/api/tasks/999999/complete/", {}).then(() => "resolved", () => "rejected"));
  });
  await ready;
  const logout = page.waitForResponse(r => r.url().endsWith("/api/auth/logout/"));
  await page.getByTestId("merchant-logout").click();
  await logout;
  await expect(page).toHaveURL(/\/login/);
  await login("foreign_owner@example.com");
  await expect(page.locator('input[autocomplete="name"]')).toHaveValue("PlatformaCRM Foreign Business Owner");
  release();
  const outcome = await page.evaluate(async () => await Reflect.get(window, "lateMutation"));
  console.log(JSON.stringify({ outcome, requests: credentials.length, credentialsChanged: credentials.length > 1 && credentials[0] !== credentials[1] }));
  expect(outcome).toBe("rejected");
  expect(credentials).toHaveLength(1);
});

async function loginAs(page: import("@playwright/test").Page, email: string) {
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
}

test("same-session unauthorized request refreshes and retries once", async ({ page }) => {
  await page.goto("/login");
  await loginAs(page, "business_owner@example.com");
  let requests = 0;
  let refreshes = 0;
  page.on("request", request => { if (request.url().endsWith("/api/auth/token/refresh/")) refreshes++; });
  await page.route("**/api/tasks/999999/complete/", route => {
    requests++;
    return route.fulfill({ status: requests === 1 ? 401 : 200, json: { ok: true } });
  });
  const result = await page.evaluate(async () => {
    const modulePath = "/src/api/client.ts";
    const { apiClient } = await import(modulePath);
    return (await apiClient.post("/api/tasks/999999/complete/", {})).data;
  });
  expect(result).toEqual({ ok: true });
  expect(requests).toBe(2);
  expect(refreshes).toBe(1);
  await expect(page.getByTestId("header-account-link")).toBeVisible();
});

test("pending refresh finishes before logout and a rapid new login", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/login");
  await loginAs(page, "business_owner@example.com");
  await page.getByTestId("header-account-link").click();
  await expect(page.getByTestId("merchant-logout")).toBeVisible();
  const order: string[] = [];
  let release!: () => void;
  let started!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const ready = new Promise<void>(resolve => { started = resolve; });
  page.on("request", request => {
    if (request.url().endsWith("/api/auth/logout/")) order.push("logout");
    if (request.url().endsWith("/api/auth/token/")) order.push("login");
  });
  await page.route("**/api/auth/token/refresh/", async route => {
    const response = await route.fetch();
    started();
    await held;
    order.push("refresh-response");
    await route.fulfill({ response });
  });
  await page.evaluate(async () => {
    const modulePath = "/src/api/token.ts";
    const { refreshToken } = await import(modulePath);
    Reflect.set(window, "pendingRefresh", refreshToken().then(() => "resolved", () => "rejected"));
  });
  await ready;
  await page.getByTestId("merchant-logout").click();
  await expect(page).toHaveURL(/\/login/);
  await page.locator('form input[type="email"]').fill("foreign_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  expect(order).toEqual([]);
  release();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  expect(await page.evaluate(async () => await Reflect.get(window, "pendingRefresh"))).toBe("rejected");
  expect(order).toEqual(["refresh-response", "logout", "login"]);
  await page.reload();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await page.getByTestId("header-account-link").click();
  await expect(page.locator('input[autocomplete="name"]')).toHaveValue("PlatformaCRM Foreign Business Owner");
});

test("cross-tab cookie switch cannot replay an old account mutation", async ({ page, context }) => {
  test.setTimeout(60_000);
  await page.goto("/login");
  await loginAs(page, "business_owner@example.com");
  const second = await context.newPage();
  await second.goto("/app/account");
  await expect(second.getByTestId("merchant-logout")).toBeVisible();
  const logout = second.waitForResponse(response => response.url().endsWith("/api/auth/logout/"));
  await second.getByTestId("merchant-logout").click();
  await logout;
  await loginAs(second, "foreign_owner@example.com");
  let requests = 0;
  await page.route("**/api/tasks/999999/complete/", route => {
    requests++;
    return route.fulfill({ status: requests === 1 ? 401 : 200, json: { ok: true } });
  });
  const result = await page.evaluate(async () => {
    const modulePath = "/src/api/client.ts";
    const { apiClient } = await import(modulePath);
    return apiClient.post("/api/tasks/999999/complete/", {}).then(() => "resolved", () => "rejected");
  });
  expect(result).toBe("rejected");
  expect(requests).toBe(1);
  await expect(page).toHaveURL(/\/login/);
  await second.reload();
  await expect(second.getByTestId("header-account-link")).toBeVisible();
  await expect(second.locator('input[autocomplete="name"]')).toHaveValue("PlatformaCRM Foreign Business Owner");
});
