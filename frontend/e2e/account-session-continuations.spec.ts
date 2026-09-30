import { expect, test, type Page } from "@playwright/test";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable synthetic accounts");
});

async function login(page: Page, email: string) {
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const response = page.waitForResponse(item => item.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const access = (await (await response).json()).access as string;
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  return access;
}

const cookieChanges = [
  { operation: "confirmEmailChange", path: "change-email/confirm", payload: "123456" },
  { operation: "changePassword", path: "change-password", payload: { current_password: "synthetic", new_password: "synthetic" } },
  { operation: "disableMfa", path: "mfa/disable", payload: { password: "synthetic", code: "123456", reason: "Synthetic test" } },
  { operation: "revokeMfaSessions", path: "mfa/sessions/revoke", payload: "123456" },
  { operation: "confirmPasswordReset", path: "password-reset/confirm", payload: { uid: "synthetic", token: "synthetic", password: "synthetic" } },
];

for (const change of cookieChanges) test(`${change.operation} completes its cookie response before logout and the next login`, async ({ page, context }) => {
  test.setTimeout(60_000);
  await page.goto("/login");
  const previousAccess = await login(page, "business_owner@example.com");
  await page.getByTestId("header-account-link").click();
  await expect(page.getByTestId("merchant-logout")).toBeVisible();
  const cookie = (await context.cookies()).find(item => item.name === "zani_refresh")!;
  expect(Boolean(cookie)).toBe(true);
  const order: string[] = [];
  let release!: () => void;
  let started!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const ready = new Promise<void>(resolve => { started = resolve; });
  page.on("request", request => {
    if (request.url().endsWith("/api/auth/logout/")) order.push("logout");
    if (request.url().endsWith("/api/auth/token/")) order.push("login");
  });
  await page.route(`**/api/auth/${change.path}/`, async route => {
    started();
    await held;
    order.push("account-response");
    const value = change.operation === "confirmPasswordReset" ? "; Max-Age=0" : cookie.value;
    await route.fulfill({ status: 200, headers: { "Set-Cookie": `zani_refresh=${value}; Path=${cookie.path}; HttpOnly; SameSite=Lax` }, json: { ok: true, email: "synthetic-renamed@example.invalid", access: previousAccess } });
  });
  await page.evaluate(async ({ operation, payload }) => {
    const modulePath = "/src/api/auth.ts";
    const api = await import(modulePath);
    Reflect.set(window, "accountCookieOutcome", api[operation](payload).then(() => "resolved", () => "rejected"));
  }, change);
  await ready;
  await page.getByTestId("merchant-logout").click();
  await expect(page).toHaveURL(/\/login/);
  await page.locator('form input[type="email"]').fill("foreign_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  try { expect(order).toEqual([]); } finally { release(); }
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  expect(await page.evaluate(async () => await Reflect.get(window, "accountCookieOutcome"))).toBe("rejected");
  expect(order).toEqual(["account-response", "logout", "login"]);
  await page.reload();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  await page.getByTestId("header-account-link").click();
  await expect(page.locator('input[autocomplete="name"]')).toHaveValue("PlatformaCRM Foreign Business Owner");
});

test("account cookie mutation refreshes an expired access token once without blocking its own queue", async ({ page }) => {
  await page.goto("/login");
  const access = await login(page, "business_owner@example.com");
  let refreshes = 0;
  const credentials: string[] = [];
  page.on("request", request => { if (request.url().endsWith("/api/auth/token/refresh/")) refreshes++; });
  await page.route("**/api/auth/change-email/confirm/", route => {
    credentials.push(route.request().headers().authorization || "");
    return route.fulfill({ status: credentials.length === 1 ? 401 : 200, json: { ok: true, email: "synthetic@example.invalid", access } });
  });
  const result = await page.evaluate(async () => {
    const modulePath = "/src/api/auth.ts";
    const { confirmEmailChange } = await import(modulePath);
    return (await confirmEmailChange("123456")).ok;
  });
  expect(result).toBe(true);
  expect(refreshes).toBe(1);
  expect(credentials).toHaveLength(2);
  expect(credentials[0] === credentials[1]).toBe(false);
});

test("a delayed language preload cannot save preferences as the next account", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/login");
  await login(page, "business_owner@example.com");
  await page.getByTestId("header-account-link").click();
  let release!: () => void;
  let started!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const ready = new Promise<void>(resolve => { started = resolve; });
  let dictionaryFinished = false;
  await page.route("**/src/lib/i18n/en.ts*", async route => {
    started();
    await held;
    await route.continue();
  });
  page.on("requestfinished", request => {
    if (request.url().includes("/src/lib/i18n/en.ts")) dictionaryFinished = true;
  });
  let saves = 0;
  page.on("request", request => {
    if (request.method() === "PATCH" && request.url().endsWith("/api/auth/me/")) saves++;
  });
  const card = page.locator("#interface");
  await card.locator("select").first().selectOption("en");
  await card.getByRole("button", { name: "Сохранить", exact: true }).click();
  await ready;
  const logout = page.waitForResponse(response => response.url().endsWith("/api/auth/logout/"));
  await page.getByTestId("merchant-logout").click();
  await logout;
  await expect(page).toHaveURL(/\/login/);
  await login(page, "foreign_owner@example.com");
  release();
  await expect.poll(() => dictionaryFinished).toBe(true);
  // Let the released import and its mutation continuation drain.
  await page.waitForTimeout(1000);
  expect(saves).toBe(0);
  await expect(page.locator("#interface select").first()).toHaveValue("ru");
});
