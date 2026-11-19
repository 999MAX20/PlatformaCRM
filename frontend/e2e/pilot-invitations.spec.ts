import { authPost } from "./support/auth-request";
import { expect, test } from "@playwright/test";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { createHmac } from "node:crypto";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const mailbox = process.env.E2E_INVITATION_MAIL_DIR;
test.beforeEach(() => test.skip(!mailbox, "Use scripts/verify_invitations.py"));

function messages(email: string) {
  if (!mailbox || !existsSync(mailbox)) return [];
  return readdirSync(mailbox).filter(name => name.endsWith(".json"))
    .map(name => JSON.parse(readFileSync(join(mailbox, name), "utf8")) as { to: string[]; body: string })
    .filter(item => item.to.includes(email));
}

test("new employee accepts a manual invitation and logs into only the invited business", async ({ page }) => {
  const ownerLogin = await authPost(page.request, `${api}/api/auth/token/`, {
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
  await page.getByRole("button", { name: "Выйти из текущего аккаунта", exact: true }).click();
  expect((await signedOut).ok()).toBeTruthy();
  await page.locator('form input[name="full_name"]').fill("Pilot invited employee");
  await page.locator('form input[name="password"]').fill(password);
  await page.locator('form input[name="password_confirm"]').fill(password);
  const acceptance = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/team/invitations/accept/"));
  const login = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/auth/token/"));
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  expect((await acceptance).ok()).toBeTruthy();
  const loggedIn = await login;
  expect(loggedIn.ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByText("Приглашение принято", { exact: true })).toHaveCount(0);
  const me = await page.request.get(`${api}/api/auth/me/`, { headers: { Authorization: `Bearer ${(await loggedIn.json()).access}` } });
  expect(me.ok()).toBeTruthy();
  const profile = await me.json();
  expect(profile.email).toBe(email);
  expect(profile.businesses.map((item: { id: number }) => item.id)).toEqual([business]);
  expect(profile.memberships).toHaveLength(1);
  expect(profile.memberships[0].role).toBe("operator");
  const ownerContext = await page.context().browser()!.newContext({ baseURL: process.env.E2E_BASE_URL, viewport: page.viewportSize() });
  try {
    const ownerSession = await authPost(ownerContext.request, `${api}/api/auth/token/`, { data: {
      email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD,
    } });
    expect(ownerSession.ok()).toBeTruthy();
    const ownerPage = await ownerContext.newPage();
    await ownerPage.goto("/app/settings#team-access");
    await ownerPage.getByRole("button", { name: "Приглашения", exact: true }).click();
    const accepted = ownerPage.locator("div.flex.flex-wrap.items-center.justify-between").filter({ has: ownerPage.getByText(email, { exact: true }) });
    await expect(accepted.getByText(/Принято/)).toBeVisible();
    await expect(accepted.getByText(/Ссылка действует до/)).toHaveCount(0);
    await ownerPage.getByRole("button", { name: "Сотрудники", exact: true }).click();
    await ownerPage.getByRole("button").filter({ hasText: email }).click();
    const toggle = ownerPage.getByTestId("team-access-toggle");
    await expect(toggle).toBeInViewport();
    await ownerPage.screenshot({ path: `../output/invitations-24h-20261112/access-action-${test.info().project.name}.png`, fullPage: true });
    await toggle.click();
    const confirmation = ownerPage.getByRole("dialog").filter({ hasText: "Его история, задачи и записи сохранятся" });
    await confirmation.getByRole("button", { name: "Отключить доступ к компании", exact: true }).click();
    await expect(toggle).toHaveText(/Включить/);
    const removalHeaders = { Authorization: `Bearer ${(await ownerSession.json()).access}` };
    const memberList = await (await ownerContext.request.get(`${api}/api/team/members/?business=${business}`, { headers: removalHeaders })).json();
    const removedMember = memberList.results.find((row: { user: { email: string } }) => row.user.email === email);
    const removal = await ownerContext.request.delete(`${api}/api/team/members/${removedMember.id}/`, { headers: removalHeaders });
    expect(removal.status()).toBe(204);
    await page.reload();
    await expect(page.getByRole("heading", { name: "У вас больше нет доступа к этому бизнесу", exact: true })).toBeVisible();
    await expect(page.getByRole("searchbox")).toHaveCount(0);
    await expect(page.getByText(/Бизнес ещё не создан/)).toHaveCount(0);
    await page.getByRole("button", { name: "Выйти", exact: true }).focus();
    await expect(page.getByRole("button", { name: "Выйти", exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `../output/invitations-24h-20261112/revoked-${test.info().project.name}.png`, fullPage: true });
    for (const [language, title] of [["en", "You no longer have access to this business"], ["kk", "Бұл бизнеске енді қол жеткізе алмайсыз"], ["ru", "У вас больше нет доступа к этому бизнесу"]]) {
      await page.evaluate(lang => localStorage.setItem("ai_smb_language", lang), language);
      await page.reload();
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    }
    await page.getByRole("button", { name: "Выйти", exact: true }).press("Enter");
    await expect(page).toHaveURL(/\/login/);
  } finally { await ownerContext.close(); }
});

test("owner creates emailed invitation, sees delivery failure, resends expired link and revokes", async ({ page }, info) => {
  const signedIn = await authPost(page.request, `${api}/api/auth/token/`, { data: {
    email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD,
  } });
  expect(signedIn.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await signedIn.json()).access}` };
  await page.goto("/app/settings#team-access");
  await page.getByRole("button", { name: "Пригласить сотрудника", exact: true }).click();
  const dialog = page.getByTestId("invitation-dialog");
  await expect(dialog.getByText("Изменения роли применяются ко всем сотрудникам с этой ролью.")).toBeVisible();
  await dialog.getByRole("button", { name: "Показать разделы без доступа" }).click();
  await expect(dialog.getByText("Нет доступа", { exact: true }).first()).toBeVisible();
  await dialog.getByRole("button", { name: "Скрыть разделы без доступа" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Пригласить сотрудника", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Пригласить сотрудника", exact: true }).press("Enter");
  for (const width of (info.project.name.startsWith("mobile") ? [390] : [1440, 768])) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `../output/invitations-24h-20261112/modal-${width}.png`, fullPage: true });
  }
  const email = `email-${info.project.name}-${Date.now()}@example.com`;
  await page.getByLabel("Email для входа", { exact: true }).fill(email);
  const creation = page.waitForResponse(r => r.url().endsWith("/api/team/invitations/") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Отправить приглашение", exact: true }).click();
  const result = await creation;
  expect(result.status()).toBe(201);
  const row = await result.json();
  expect(row.delivery_status).toBe("accepted");
  expect(Date.parse(row.expires_at) - Date.parse(row.created_at)).toBeGreaterThan(86_390_000);
  expect(Date.parse(row.expires_at) - Date.parse(row.created_at)).toBeLessThanOrEqual(86_400_000);
  await expect(page.getByText("Отправлено", { exact: true })).toBeVisible();
  expect(messages(email)).toHaveLength(1);
  expect(messages(email)[0].body).toContain(row.invite_path);
  await page.getByRole("button", { name: "Закрыть", exact: true }).last().click();

  mkdirSync(mailbox!, { recursive: true });
  writeFileSync(join(mailbox!, "fail"), "synthetic failure");
  try {
    await page.getByRole("button", { name: "Пригласить сотрудника", exact: true }).click();
    await page.getByLabel("Email для входа", { exact: true }).fill(`failed-${email}`);
    await page.getByRole("button", { name: "Отправить приглашение", exact: true }).click();
    await expect(page.getByText("Не удалось отправить письмо", { exact: true })).toBeVisible();
    expect(messages(`failed-${email}`)).toHaveLength(0);
    await page.getByRole("button", { name: "Закрыть", exact: true }).last().click();
  } finally { unlinkSync(join(mailbox!, "fail")); }

  await page.getByRole("button", { name: "Приглашения", exact: true }).click();
  const expiredEmail = `expired-${info.project.name}@example.com`;
  const list = await page.request.get(`${api}/api/team/invitations/`, { headers });
  const old = (await list.json()).results.find((item: { email: string }) => item.email === expiredEmail);
  expect(old.status).toBe("expired");
  const item = page.locator("div.flex.flex-wrap.items-center.justify-between").filter({ has: page.getByText(expiredEmail, { exact: true }) });
  await item.getByRole("button", { name: "Отправить новую ссылку" }).click();
  await expect(item.getByText("Отправлено", { exact: true })).toBeVisible();
  expect(messages(expiredEmail)).toHaveLength(1);
  const invalid = await page.request.get(`${api}/api/team/invitations/preview/${old.token}/`);
  expect(invalid.status()).toBe(400);
  await item.getByRole("button", { name: "Отозвать", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Отозвать", exact: true }).click();
  await expect(item.getByRole("button", { name: "Отправить новую ссылку" })).toHaveCount(0);
  await expect(item.getByText(/Ссылка действует до/)).toHaveCount(0);
  await expect(item.getByText("Отправлено", { exact: true })).toHaveCount(0);
  const failedItem = page.locator("div.flex.flex-wrap.items-center.justify-between").filter({ has: page.getByText(`failed-${email}`, { exact: true }) });
  await failedItem.getByRole("button", { name: "Отозвать", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Отозвать", exact: true }).click();
  await expect(failedItem.getByText("Не удалось отправить письмо", { exact: true })).toHaveCount(0);
  await expect(failedItem.getByText(/Проверьте настройку почты/)).toHaveCount(0);
  await expect(failedItem.getByText(/Ссылка действует до/)).toHaveCount(0);
});

test("existing owner accepts another business without changing password and enters that business", async ({ page, playwright }, info) => {
  const ownerApi = await playwright.request.newContext();
  const ownerLogin = await authPost(ownerApi, `${api}/api/auth/token/`, { data: {
    email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD,
  } });
  const headers = { Authorization: `Bearer ${(await ownerLogin.json()).access}` };
  const owner = await (await ownerApi.get(`${api}/api/auth/me/`, { headers })).json();
  const invitedBusiness = owner.businesses[0];
  const email = `existing-${info.project.name}-${Date.now()}@example.com`;
  const password = "ExistingPilot984!";
  const signup = await authPost(page.request, `${api}/api/auth/signup/owner/`, { data: {
    email, password, business_name: `Own ${info.project.name}`,
    accepted_documents: ["terms", "privacy", "personal-data", "company-data"],
  } });
  expect(signup.status()).toBe(201);
  const created = await ownerApi.post(`${api}/api/team/invitations/`, { headers, data: {
    business: invitedBusiness.id, email, role: "operator", delivery_channel: "email",
  } });
  expect(created.status()).toBe(201);
  const invitation = await created.json();
  await page.context().clearCookies();
  await page.goto(invitation.invite_path);
  await page.getByLabel("Пароль", { exact: true }).fill("WrongPassword123!");
  const deniedLogin = page.waitForResponse(r => r.url().endsWith("/api/auth/token/"));
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  expect((await deniedLogin).status()).toBe(401);
  await expect(page).toHaveURL(new RegExp(invitation.invite_path));
  const stillPending = await ownerApi.get(`${api}/api/team/invitations/preview/${invitation.token}/`);
  expect((await stillPending.json()).status).toBe("pending");
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  await expect(page).toHaveURL(/\/app/);
  expect(await page.evaluate(id => sessionStorage.getItem(`platforma:invitation-business:${id}`), (await signup.json()).user.id)).toBe(String(invitedBusiness.id));
  const dashboard = page.waitForResponse(r => new URL(r.url()).pathname === "/api/work-queues/" && r.request().method() === "GET");
  await page.reload();
  const dashboardResult = await dashboard;
  expect(dashboardResult.ok()).toBeTruthy();
  expect(new URL(dashboardResult.url()).searchParams.get("business")).toBe(String(invitedBusiness.id));
  const replay = await page.request.post(`${api}/api/team/invitations/accept/`, { data: { token: invitation.token } });
  expect(replay.status()).toBe(400);
  const reLogin = await authPost(page.request, `${api}/api/auth/token/`, { data: { email, password } });
  expect(reLogin.ok()).toBeTruthy();
  await ownerApi.dispose();
});

test("existing recipient completes MFA inside invitation and enters without accepting twice", async ({ page }, info) => {
  const owner = await authPost(page.request, `${api}/api/auth/token/`, { data: { email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await owner.json()).access}` };
  const list = await page.request.get(`${api}/api/team/invitations/`, { headers });
  const invitation = (await list.json()).results.find((row: { email: string }) => row.email === `invite-mfa-${info.project.name}@example.com`);
  await page.context().clearCookies();
  await page.goto(invitation.invite_path);
  await page.getByLabel("Пароль", { exact: true }).fill("InviteMfa123!");
  let accepts = 0;
  page.on("request", request => { if (request.url().endsWith("/api/team/invitations/accept/")) accepts++; });
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  const codeInput = page.getByTestId("mfa-code-input").locator("input");
  await expect(codeInput).toBeVisible();
  await expect(page).toHaveURL(new RegExp(invitation.invite_path));
  expect(accepts).toBe(0);
  await codeInput.fill("000000");
  const invalid = page.waitForResponse(r => r.url().endsWith("/api/auth/mfa/verify/"));
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  expect((await invalid).ok()).toBeFalsy();
  expect(accepts).toBe(0);
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = createHmac("sha1", Buffer.from("48656c6c6f21deadbeef", "hex")).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  const code = String((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, "0");
  await codeInput.fill(code);
  await page.screenshot({ path: `../output/invitations-24h-20261112/mfa-${info.project.name}.png`, fullPage: true });
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page).toHaveURL(/\/app/);
  expect(accepts).toBe(1);
});

test("accepted new account recovers a failed login without consuming invitation again", async ({ page }, info) => {
  const owner = await authPost(page.request, `${api}/api/auth/token/`, { data: { email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD } });
  const headers = { Authorization: `Bearer ${(await owner.json()).access}` };
  const profile = await (await page.request.get(`${api}/api/auth/me/`, { headers })).json();
  const created = await page.request.post(`${api}/api/team/invitations/`, { headers, data: {
    business: profile.businesses[0].id, email: `login-recovery-${info.project.name}@example.com`, role: "operator", delivery_channel: "manual",
  } });
  expect(created.status()).toBe(201);
  const invitation = await created.json();
  await page.context().clearCookies();
  await page.goto(invitation.invite_path);
  await page.locator('input[name="password"]').fill("RecoveryLogin123!");
  await page.locator('input[name="password_confirm"]').fill("RecoveryLogin123!");
  let accepts = 0;
  let failLogin = true;
  page.on("request", request => { if (request.url().endsWith("/api/team/invitations/accept/")) accepts++; });
  await page.route("**/api/auth/token/", route => {
    if (failLogin) { failLogin = false; return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic outage"}' }); }
    return route.continue();
  });
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  await expect(page.getByRole("button", { name: "Войти в аккаунт", exact: true })).toBeEnabled();
  expect(accepts).toBe(1);
  await expect(page.locator('input[name="password"]')).toHaveValue("RecoveryLogin123!");
  await page.getByRole("button", { name: "Войти в аккаунт", exact: true }).click();
  await expect(page).toHaveURL(/\/app/);
  expect(accepts).toBe(1);
});

test("missing, invalid and revoked states have no password form; locales and keyboard reflow", async ({ page }, info) => {
  const login = await authPost(page.request, `${api}/api/auth/token/`, { data: {
    email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD,
  } });
  const headers = { Authorization: `Bearer ${(await login.json()).access}` };
  const listing = await page.request.get(`${api}/api/team/invitations/`, { headers });
  expect(listing.ok()).toBeTruthy();
  const invitation = (await listing.json()).results.find((item: { email: string }) => item.email === `states-${info.project.name}@example.com`);
  expect(invitation).toBeTruthy();
  expect((await page.request.post(`${api}/api/team/invitations/${invitation.id}/revoke/`, { headers })).ok()).toBeTruthy();
  await page.context().clearCookies();
  await page.setViewportSize({ width: info.project.name.startsWith("mobile") ? 320 : 1440, height: 900 });
  for (const [language, missing, revoked] of [["ru", "В ссылке нет приглашения", "Приглашение отозвано"], ["kk", "Бұл сілтемеде шақыру жоқ", "Шақыру кері қайтарылды"], ["en", "This link has no invitation", "Invitation revoked"]]) {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/invite");
    await expect(page.getByText(missing, { exact: true })).toBeVisible();
    await page.goto(invitation.invite_path);
    await expect(page.getByText(revoked, { exact: true })).toBeVisible();
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY");
    await page.screenshot({ path: `../output/invitations-24h-20261112/${info.project.name}-${language}.png`, fullPage: true });
  }
  await page.goto("/invite/not-a-token");
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
});

test("preview retry and failed acceptance retain the draft; new-account form reflows in all locales", async ({ page }, info) => {
  const login = await authPost(page.request, `${api}/api/auth/token/`, { data: {
    email: process.env.E2E_OWNER_EMAIL, password: process.env.E2E_PASSWORD,
  } });
  const headers = { Authorization: `Bearer ${(await login.json()).access}` };
  const listing = await page.request.get(`${api}/api/team/invitations/`, { headers });
  const invitation = (await listing.json()).results.find((item: { email: string }) => item.email === `recovery-${info.project.name}@example.com`);
  expect(invitation).toBeTruthy();
  await page.context().clearCookies();
  let failPreview = true;
  await page.route("**/api/team/invitations/preview/**", route => {
    if (failPreview) { failPreview = false; return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic outage"}' }); }
    return route.continue();
  });
  await page.goto(invitation.invite_path);
  await expect(page.getByText("Не удалось проверить приглашение. Повторите попытку.", { exact: true })).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Повторить", exact: true }).click();
  await page.locator('input[name="full_name"]').fill("Synthetic retained draft");
  await page.locator('input[name="password"]').fill("RecoveryPassword123!");
  await page.locator('input[name="password_confirm"]').fill("RecoveryPassword123!");
  await page.route("**/api/team/invitations/accept/", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic outage"}' }));
  const failed = page.waitForResponse(r => r.url().endsWith("/api/team/invitations/accept/"));
  await page.getByRole("button", { name: "Принять и войти", exact: true }).click();
  expect((await failed).status()).toBe(503);
  await expect(page.locator('input[name="password"]')).toHaveValue("RecoveryPassword123!");
  await expect(page.locator('input[name="full_name"]')).toHaveValue("Synthetic retained draft");
  await page.setViewportSize({ width: info.project.name.startsWith("mobile") ? 320 : 1440, height: 900 });
  for (const language of ["ru", "kk", "en"]) {
    await page.evaluate(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.reload();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({ path: `../output/invitations-24h-20261112/form-${info.project.name}-${language}.png`, fullPage: true });
  }
});
