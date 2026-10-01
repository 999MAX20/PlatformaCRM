import { expect, test } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

test("password reset acknowledges the generic response without exposing account existence", async ({ page }) => {
  await page.goto("/forgot-password");
  await page.locator('input[name="email"]').fill(`unknown-pilot-${Date.now()}@example.com`);
  const requested = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/password-reset/request/"));
  await page.locator('form button[type="submit"]').click();
  const response = await requested;
  expect(response.ok()).toBeTruthy();
  expect(response.request().postDataJSON().delivery_channel).toBe("email");
  const body = await response.json();
  expect(body.reset_path).toBeUndefined();
  expect(body.token).toBeUndefined();
  await expect(page.getByRole("status")).toContainText(body.message);
  await expect(page.getByRole("combobox")).toHaveCount(0);
});

test("owner signup and password change persist and invalidate old credentials", async ({ page }) => {
  test.setTimeout(90_000);
  const email = `pilot-auth-${Date.now()}@example.com`;
  const password = "PilotInitial928!";
  const replacement = "PilotReplacement928!";
  const company = `Pilot signup ${Date.now()}`;
  await page.goto("/signup");
  for (const [name, value] of Object.entries({
    full_name: "Pilot owner", phone: "+77770001234", email,
    business_name: company, password, password_confirm: password,
  })) await page.locator(`form input[name="${name}"]`).fill(value);
  for (const checkbox of await page.getByTestId("signup-documents").getByRole("checkbox").all()) await checkbox.check();
  const registration = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/signup/owner/"));
  await page.locator('form button[type="submit"]').click();
  const registered = await registration;
  expect(registered.status(), await registered.text()).toBe(201);
  const result = await registered.json();
  expect(result.business.name).toBe(company);
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  await expect(page.getByLabel("Имя", { exact: true })).toHaveValue("Pilot owner");
  await page.getByRole("button", { name: "Изменить пароль", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Текущий пароль", { exact: true }).fill(password);
  await dialog.getByLabel("Новый пароль", { exact: true }).fill(replacement);
  await dialog.getByLabel("Повторите пароль", { exact: true }).fill(replacement);
  const changed = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/change-password/"));
  await dialog.getByRole("button", { name: "Изменить пароль", exact: true }).click();
  expect((await changed).ok()).toBeTruthy();
  const rejected = await page.request.post(`${api}/api/auth/token/`, { data: { email, password } });
  expect(rejected.status()).toBe(401);
  const accepted = await page.request.post(`${api}/api/auth/token/`, { data: { email, password: replacement } });
  expect(accepted.ok()).toBeTruthy();
  const me = await page.request.get(`${api}/api/auth/me/`, { headers: { Authorization: `Bearer ${(await accepted.json()).access}` } });
  expect(me.ok()).toBeTruthy();
  expect((await me.json()).businesses.some((business: { id: number }) => business.id === result.business.id)).toBe(true);
});
