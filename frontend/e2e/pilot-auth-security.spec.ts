import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

function currentTotp(secret: string) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = secret.replace(/=+$/u, "").toUpperCase().split("")
    .map(character => alphabet.indexOf(character).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from((bits.match(/.{8}/g) || []).map(byte => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac("sha1", key).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

test("MFA enrollment, recovery-code login and authorized disable persist through UI", async ({ page }) => {
  test.setTimeout(90_000);
  const email = `pilot-mfa-${Date.now()}@example.com`;
  const password = "PilotMfaAccount928!";
  const registered = await page.request.post(`${api}/api/auth/signup/owner/`, {
    data: { email, password, full_name: "Pilot MFA owner", business_name: `Pilot MFA ${Date.now()}`, phone: "+77770009911" },
  });
  expect(registered.status()).toBe(201);
  await page.goto("/app/account");
  const started = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/mfa/enrollment/start/"));
  await page.getByRole("button", { name: "Подключить MFA", exact: true }).click();
  const startResponse = await started;
  expect(startResponse.ok()).toBeTruthy();
  const enrollment = await startResponse.json();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Код подтверждения", { exact: true }).fill(currentTotp(enrollment.manual_key));
  const confirmed = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/mfa/enrollment/confirm/"));
  await dialog.getByRole("button", { name: "Подключить защиту", exact: true }).click();
  const confirmation = await confirmed;
  expect(confirmation.ok()).toBeTruthy();
  const codes: string[] = (await confirmation.json()).recovery_codes;
  expect(codes.length).toBeGreaterThanOrEqual(2);
  await dialog.getByRole("button", { name: "Закрыть", exact: true }).last().click();
  await page.reload();
  await expect(page.getByText("Защита включена", { exact: true })).toBeVisible();

  await page.context().clearCookies();
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/mfa$/);
  await page.getByLabel("Код подтверждения", { exact: true }).fill(codes[0]);
  const verified = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/mfa/verify/"));
  await page.getByRole("button", { name: "Подтвердить вход", exact: true }).click();
  expect((await verified).ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  await page.getByRole("button", { name: "Безопасность аккаунта", exact: true }).click();
  await page.getByRole("button", { name: "Отключить MFA", exact: true }).click();
  await dialog.getByLabel("Текущий пароль", { exact: true }).fill(password);
  await dialog.getByLabel("Причина отключения", { exact: true }).fill("Synthetic pilot acceptance complete");
  await dialog.getByLabel("Код подтверждения", { exact: true }).fill(codes[1]);
  const disabled = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/mfa/disable/"));
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  const result = await disabled;
  expect(result.ok()).toBeTruthy();
  const status = await page.request.get(`${api}/api/auth/mfa/status/`, { headers: { Authorization: `Bearer ${(await result.json()).access}` } });
  expect(status.ok()).toBeTruthy();
  expect((await status.json()).enabled).toBe(false);
  await page.reload();
  await expect(page.getByRole("button", { name: "Подключить MFA", exact: true })).toBeVisible();
});

test("existing MFA account returns to its invitation and accepts the intended business", async ({ page }) => {
  test.setTimeout(90_000);
  const stamp = Date.now();
  const email = `pilot-invite-mfa-${stamp}@example.com`;
  const password = "PilotInviteMfa928!";
  const signup = async (address: string) => {
    const response = await page.request.post(`${api}/api/auth/signup/owner/`, {
      data: { email: address, password, full_name: "Pilot invited owner", business_name: address, phone: "+77770009922" },
    });
    expect(response.status()).toBe(201);
    return response.json();
  };
  const invitee = await signup(email);
  const start = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers: { Authorization: `Bearer ${invitee.access}` }, data: {} });
  expect(start.ok()).toBeTruthy();
  const enrollment = await start.json();
  const confirmation = await page.request.post(`${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: currentTotp(enrollment.manual_key) } });
  expect(confirmation.ok()).toBeTruthy();
  const codes = (await confirmation.json()).recovery_codes;
  const inviter = await signup(`pilot-inviter-${stamp}@example.com`);
  const invited = await page.request.post(`${api}/api/team/invitations/`, {
    headers: { Authorization: `Bearer ${inviter.access}` },
    data: { business: inviter.business.id, email, role: "operator", delivery_channel: "manual" },
  });
  expect(invited.status()).toBe(201);
  const invitation = await invited.json();
  await page.context().clearCookies();
  await page.goto(invitation.invite_path);
  await page.getByRole("link", { name: "Войти и принять", exact: true }).click();
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/mfa$/);
  await page.getByLabel("Код подтверждения", { exact: true }).fill(codes[0]);
  const verified = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/mfa/verify/"));
  await page.getByRole("button", { name: "Подтвердить вход", exact: true }).click();
  const session = await (await verified).json();
  await expect(page).toHaveURL(new RegExp(`${invitation.invite_path}$`));
  const accepted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/team/invitations/accept/"));
  await page.getByRole("button", { name: "Принять приглашение", exact: true }).click();
  const acceptedResponse = await accepted;
  expect(acceptedResponse.ok()).toBeTruthy();
  expect((await acceptedResponse.json()).business).toBe(inviter.business.id);
  await expect(page).toHaveURL(/\/app/);
  const members = await page.request.get(`${api}/api/team/members/?business=${inviter.business.id}`, { headers: { Authorization: `Bearer ${inviter.access}` } });
  expect(members.ok()).toBeTruthy();
  const payload = await members.json();
  const membership = (payload.results || payload).filter((member: { user: { email: string } }) => member.user.email === email);
  expect(membership).toHaveLength(1);
  expect(membership[0].role).toBe("operator");
  // Acceptance must leave the mixed owner/operator workspace usable, not just
  // create the membership while its unfiltered tenant lists fail in the shell.
  for (const path of ["/api/tasks/", "/api/notifications/summary/?surface=bell"]) {
    const workspace = await page.request.get(`${api}${path}`, { headers: { Authorization: `Bearer ${session.access}` } });
    expect(workspace.status()).toBe(200);
  }
});
