import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test.beforeEach(async ({}, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1" || testInfo.project.name !== "desktop-chromium", "Isolated multi-tab session acceptance");
});

async function refresh(page: Page) {
  return page.evaluate(async () => {
    const path = "/src/api/token.ts";
    return Boolean(await (await import(path)).refreshToken());
  });
}

test("two tabs rotate a shared cookie without overlapping requests or clearing it", async ({ page, context }) => {
  await crmSession(page);
  const sibling = await context.newPage();
  await sibling.goto("/app/deals");
  await expect(sibling.getByTestId("header-account-link")).toBeVisible();
  await refresh(page);
  await refresh(sibling);
  let pending = 0;
  let maximum = 0;
  const statuses: number[] = [];
  await context.route("**/api/auth/token/refresh/", async route => {
    maximum = Math.max(maximum, ++pending);
    try {
      const response = await route.fetch();
      statuses.push(response.status());
      // Hold Set-Cookie delivery so both tabs really compete for the old cookie.
      await new Promise(resolve => setTimeout(resolve, 150));
      await route.fulfill({ response });
    } finally { pending--; }
  });
  await Promise.all([refresh(page), refresh(sibling)]);
  expect(maximum).toBe(1);
  expect(statuses.length).toBeGreaterThan(0);
  expect(statuses.every(status => status === 200)).toBe(true);
  await page.reload();
  await sibling.reload();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await expect(sibling.getByTestId("header-account-link")).toBeVisible();
  expect((await context.cookies()).find(cookie => cookie.name === "zani_refresh")?.httpOnly).toBe(true);
});

for (const failure of [503, 429, "offline"] as const) test(`refresh ${failure} keeps the account and unsaved form, then recovers`, async ({ page }) => {
  await crmSession(page);
  await page.goto("/app/account");
  const name = page.locator('input[autocomplete="name"]');
  await expect(name).toBeVisible();
  await refresh(page);
  await name.fill("Unsaved session recovery draft");
  await page.route("**/api/auth/token/refresh/", route => failure === "offline"
    ? route.abort("internetdisconnected")
    : route.fulfill({ status: failure, headers: { "Retry-After": "1" }, json: { detail: "Synthetic temporary failure" } }));
  await page.route("**/api/tasks/999999/", route => route.fulfill({ status: 401, json: { detail: "Expired access" } }));
  await page.evaluate(async () => {
    const path = "/src/api/client.ts";
    await (await import(path)).apiClient.get("/api/tasks/999999/").catch(() => undefined);
  });
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await expect(name).toHaveValue("Unsaved session recovery draft");
  await page.unroute("**/api/auth/token/refresh/");
  await page.getByTestId("session-recovery").getByRole("button", { name: "Повторить" }).click();
  await expect(page.getByTestId("session-recovery")).toBeHidden();
  await expect(name).toHaveValue("Unsaved session recovery draft");
});

test("a temporary startup failure preserves the cookie and restores the original route", async ({ page, context }) => {
  await crmSession(page);
  await refresh(page);
  const before = (await context.cookies()).find(cookie => cookie.name === "zani_refresh")!;
  await page.route("**/api/auth/token/refresh/", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.goto("/app/deals?status=all");
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  expect(new URL(page.url()).pathname).toBe("/app/deals");
  expect((await context.cookies()).find(cookie => cookie.name === "zani_refresh")?.value).toBe(before.value);
  await page.unroute("**/api/auth/token/refresh/");
  await page.getByTestId("session-recovery").getByRole("button", { name: "Повторить" }).click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await expect(page).toHaveURL(/\/app\/deals\?status=all/);
});

test("startup current-user failure never sends logout and retries successfully", async ({ page }) => {
  await crmSession(page);
  let logouts = 0;
  page.on("request", request => { if (request.url().endsWith("/api/auth/logout/")) logouts++; });
  await page.route("**/api/auth/me/", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.goto("/app/deals");
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  expect(logouts).toBe(0);
  await page.unroute("**/api/auth/me/");
  await page.getByTestId("session-recovery").getByRole("button", { name: "Повторить" }).click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  expect(logouts).toBe(0);
});

test("browser restart restores from the HttpOnly cookie without a stored access token", async ({ page, context, browser }) => {
  await crmSession(page);
  await refresh(page);
  const state = await context.storageState();
  expect(state.origins.flatMap(origin => origin.localStorage).some(item => item.name === "ai_smb_access_token")).toBe(false);
  const restarted = await browser.newContext({ storageState: state, baseURL: test.info().project.use.baseURL });
  try {
    await page.close();
    const restored = await restarted.newPage();
    await restored.goto("/app/deals");
    await expect(restored.getByTestId("header-account-link")).toBeVisible();
  } finally { await restarted.close(); }
});

test("offline sleep resumes an expired access token without losing a draft", async ({ page, context }) => {
  await crmSession(page);
  await page.goto("/app/account");
  const name = page.locator('input[autocomplete="name"]');
  await expect(name).toBeVisible();
  await name.fill("Offline draft");
  await context.setOffline(true);
  await page.evaluate(async () => {
    const path = "/src/lib/storage.ts";
    const { tokenStorage } = await import(path);
    const parts = tokenStorage.getAccess().split(".");
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    payload.exp = Math.floor(Date.now() / 1000) - 3600;
    parts[1] = btoa(JSON.stringify(payload)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
    tokenStorage.setAccess(parts.join("."));
  });
  const renewed = page.waitForResponse(response => response.url().endsWith("/api/auth/token/refresh/") && response.status() === 200);
  await context.setOffline(false);
  await renewed;
  await expect(name).toHaveValue("Offline draft");
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  const status = await page.evaluate(async () => {
    const path = "/src/api/auth.ts";
    return Boolean(await (await import(path)).getCurrentUser());
  });
  expect(status).toBe(true);
});

test("logout reaches sibling tabs but keeps a separate browser device signed in", async ({ page, context, browser }) => {
  await crmSession(page);
  const sibling = await context.newPage();
  await sibling.goto("/app/deals");
  await expect(sibling.getByTestId("header-account-link")).toBeVisible();
  const otherContext = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  try {
    const other = await otherContext.newPage();
    await crmSession(other);
    await page.goto("/app/account");
    const loggedOut = page.waitForResponse(response => response.url().endsWith("/api/auth/logout/"));
    await page.getByTestId("merchant-logout").click();
    await loggedOut;
    await expect(page).toHaveURL(/\/login/);
    await expect(sibling).toHaveURL(/\/login/);
    await other.reload();
    await expect(other.getByTestId("header-account-link")).toBeVisible();
  } finally { await otherContext.close(); }
});

test("explicit logout clears a temporary recovery notice and leaves the login usable", async ({ page }) => {
  await crmSession(page);
  await page.goto("/app/account");
  await expect(page.getByTestId("merchant-logout")).toBeVisible();
  await page.route("**/api/auth/token/refresh/", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.route("**/api/tasks/999999/", route => route.fulfill({ status: 401, json: { detail: "Expired access" } }));
  await page.evaluate(async () => {
    const path = "/src/api/client.ts";
    await (await import(path)).apiClient.get("/api/tasks/999999/").catch(() => undefined);
  });
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  await page.getByTestId("merchant-logout").click();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator('form input[type="email"]')).toBeVisible();
  await expect(page.getByTestId("session-recovery")).toBeHidden();
});

test("invalid refresh requires login and preserves the original return route", async ({ page }) => {
  await crmSession(page);
  await page.goto("/app/deals?status=all");
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await page.route("**/api/auth/token/refresh/", route => route.fulfill({ status: 401, json: { code: "token_not_valid" } }));
  await page.route("**/api/tasks/999999/", route => route.fulfill({ status: 401, json: { detail: "Expired access" } }));
  await page.evaluate(async () => {
    const path = "/src/api/client.ts";
    await (await import(path)).apiClient.get("/api/tasks/999999/").catch(() => undefined);
  });
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByTestId("session-recovery")).toBeHidden();
  await page.unroute("**/api/auth/token/refresh/");
  await page.locator('form input[type="email"]').fill("business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await expect(page).toHaveURL(/\/app\/deals\?status=all/);
});
