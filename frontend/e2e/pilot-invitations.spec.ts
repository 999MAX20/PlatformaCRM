import { expect, test } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

test("new employee accepts a manual invitation and logs into only the invited business", async ({ page }) => {
  const ownerLogin = await page.request.post(`${api}/api/auth/token/`, {
    data: { email: process.env.E2E_OWNER_EMAIL || "business_owner@example.com", password: process.env.E2E_PASSWORD || "ZaniTest123!" },
  });
  expect(ownerLogin.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await ownerLogin.json()).access}` };
  const ownerResponse = await page.request.get(`${api}/api/auth/me/`, { headers });
  expect(ownerResponse.ok()).toBeTruthy();
  const business = (await ownerResponse.json()).businesses[0].id;
  const email = `pilot-new-employee-${Date.now()}@example.com`;
  const password = "PilotNewEmployee928!";
  const created = await page.request.post(`${api}/api/team/invitations/`, {
    headers, data: { business, email, role: "operator", delivery_channel: "manual" },
  });
  expect(created.status()).toBe(201);
  const invitation = await created.json();
  await page.goto(invitation.invite_path);
  await expect(page.getByText("Приглашение адресовано другому аккаунту. Войдите с указанным в приглашении email.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Принять приглашение", exact: true })).toHaveCount(0);
  const denied = await page.request.post(`${api}/api/team/invitations/accept/`, { headers, data: { token: invitation.token, password } });
  expect(denied.status()).toBe(403);
  const signedOut = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/logout/"));
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  expect((await signedOut).ok()).toBeTruthy();
  await page.locator('form input[name="full_name"]').fill("Pilot invited employee");
  await page.locator('form input[name="password"]').fill(password);
  await page.locator('form input[name="password_confirm"]').fill(password);
  const acceptance = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/team/invitations/accept/"));
  await page.getByRole("button", { name: "Принять приглашение", exact: true }).click();
  expect((await acceptance).ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/login$/);
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(password);
  const login = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const loggedIn = await login;
  expect(loggedIn.ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/app/);
  const me = await page.request.get(`${api}/api/auth/me/`, { headers: { Authorization: `Bearer ${(await loggedIn.json()).access}` } });
  expect(me.ok()).toBeTruthy();
  const profile = await me.json();
  expect(profile.email).toBe(email);
  expect(profile.businesses.map((item: { id: number }) => item.id)).toEqual([business]);
  expect(profile.memberships).toHaveLength(1);
  expect(profile.memberships[0].role).toBe("operator");
});
