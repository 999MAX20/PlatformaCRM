import { refreshCookieName } from "./support/auth-cookies";
import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test.beforeEach(() => test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Isolated session fixture only"));

for (const language of ["ru", "kk", "en"]) for (const failure of ["503", "network"]) {
  test(`logout ${failure}: ${language} failure, reload and explicit retry`, async ({ page, context }, testInfo) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    const session = await crmSession(page);
    const preference = await page.request.patch(`${process.env.E2E_API_BASE_URL}/api/auth/me/`, { headers: session.headers, data: { preferences: { language } } });
    expect(preference.ok()).toBe(true);
    await page.goto("/app/account");
    await expect(page.getByTestId("merchant-logout")).toBeVisible();
    await page.route("**/api/auth/logout/", route => failure === "503"
      ? route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } })
      : route.abort("internetdisconnected"));
    await page.getByTestId("merchant-logout").click();
    const notice = page.getByTestId("logout-status");
    await expect(notice).toContainText({ ru: "Не удалось завершить выход", kk: "Шығу аяқталмады", en: "Sign-out could not be completed" }[language]!);
    await expect(page).toHaveURL(/\/app\/account/);
    expect((await context.cookies()).some(c => c.name === refreshCookieName)).toBe(true);
    await expect(notice.getByRole("button")).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("logout-failure.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.reload();
    await expect(page.getByTestId("merchant-logout")).toBeVisible();
    await page.getByTestId("merchant-logout").click();
    await expect(notice.getByRole("button")).toBeVisible();
    const resetPreference = await page.request.patch(`${process.env.E2E_API_BASE_URL}/api/auth/me/`, { headers: session.headers, data: { preferences: { language: "ru" } } });
    expect(resetPreference.ok()).toBe(true);
    await page.unroute("**/api/auth/logout/");
    await notice.getByRole("button").focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/login/);
    expect((await context.cookies()).some(c => c.name === refreshCookieName)).toBe(false);
    expect(await page.evaluate(() => localStorage.getItem("ai_smb_user_email"))).toBeNull();
    await page.reload();
    await expect(page.locator('form input[type="password"]')).toBeVisible();
  });
}

test("pending logout is single-flight; sibling tab leaves only after server success", async ({ page, context }) => {
  await crmSession(page); await page.goto("/app/account");
  const sibling = await context.newPage(); await sibling.goto("/app/account");
  await expect(sibling.getByTestId("merchant-logout")).toBeVisible();
  let release!: () => void; let started!: () => void; let count = 0;
  const ready = new Promise<void>(resolve => { started = resolve; });
  const hold = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/auth/logout/", async route => { count++; started(); await hold; await route.continue(); });
  await page.getByTestId("merchant-logout").click(); await ready;
  await expect(page.getByTestId("logout-status")).toBeVisible();
  await page.getByTestId("merchant-logout").click();
  await expect(page).toHaveURL(/\/app\/account/);
  await expect(sibling.getByTestId("merchant-logout")).toBeVisible();
  release(); await expect(page).toHaveURL(/\/login/); await expect(sibling).toHaveURL(/\/login/);
  expect(count).toBe(1);
});
