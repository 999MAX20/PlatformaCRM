import { expect, test } from "@playwright/test";

test("security layout and selective device logout preserve the current session", async ({ page, browser }) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  const origin = new URL(page.url()).origin;
  const other = await browser.newContext({ baseURL: origin, userAgent: "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0" });
  try {
    const login = await other.request.post("/api/auth/token/", { data: { email: process.env.E2E_OWNER_EMAIL || "business_owner@example.com", password: process.env.E2E_PASSWORD || "ZaniTest123!" } });
    expect(login.ok()).toBeTruthy();
    const { access } = await login.json();
    await page.goto("/app/account");
    const security = page.locator("#security");
    await expect(security.getByText("Пароль", { exact: true })).toBeVisible();
    await expect(security.getByText("Изменить пароль", { exact: true })).toHaveCount(0);
    await expect(security.getByRole("button", { name: "Изменить пароль", exact: true })).toBeVisible();
    await expect(security.getByText("Это устройство", { exact: true })).toHaveCount(1);
    const remote = security.getByTestId("account-session").filter({ hasText: "Firefox · Linux" });
    await expect(remote).toBeVisible();
    await page.screenshot({ path: `../output/account-security-${test.info().project.name}.png`, fullPage: true });
    await remote.getByRole("button", { name: "Завершить Firefox · Linux", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Завершить", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(remote).toHaveCount(0);
    expect((await other.request.get("/api/auth/me/", { headers: { Authorization: `Bearer ${access}` } })).status()).toBe(401);
    expect((await other.request.post("/api/auth/token/refresh/", { data: {} })).status()).toBe(401);
    await page.reload();
    await expect(page.locator("#security").getByText("Это устройство", { exact: true })).toHaveCount(1);
    await page.locator("#security").getByText("Последние входы", { exact: true }).click();
    await expect(page.locator("#security details[open]")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  } finally { await other.close(); }
});
