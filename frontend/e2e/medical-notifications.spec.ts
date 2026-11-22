import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
const dictionaries = { ru, kk, en };
const api = process.env.E2E_API_BASE_URL;
async function login(page: Page, email: string, language: string) {
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const response = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await response).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  return token as string;
}

async function invite(page: Page, patient: number) {
  const csrf = await (await page.request.get(`${api}/api/auth/csrf/`)).json();
  const auth = await page.request.post(`${api}/api/auth/token/`, {
    headers: { "X-CSRFToken": csrf.csrf_token },
    data: { email: "medical-role-doctor@example.test", password: process.env.E2E_PASSWORD },
  });
  expect(auth.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await auth.json()).access}` };
  const scope = { business_id: 1, patient_id: patient, branch_id: 2, source_appointment_id: patient };
  const candidates = await (await page.request.get(`${api}/api/medical/participations/candidates/`, { headers, params: scope })).json();
  const response = await page.request.post(`${api}/api/medical/participations/`, {
    headers: { ...headers, "Idempotency-Key": `notice-${patient}` },
    data: { ...scope, target_member_id: candidates.results[0].member_id, expected_patient_revision: candidates.patient_revision,
      reason: "Synthetic private invitation reason", work_direction: "Synthetic organizational work", planned_work_date: "2026-12-01" },
  });
  expect(response.status()).toBe(201);
  await page.context().clearCookies();
  return response.json();
}

async function latestNotice(page: Page, token: string) {
  const response = await page.request.get(`${api}/api/notifications/?business=1&surface=bell`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(JSON.stringify(data)).not.toContain("Synthetic clinical patient");
  expect(JSON.stringify(data)).not.toContain("Synthetic private invitation reason");
  expect(JSON.stringify(data)).not.toContain("Synthetic private decline reason");
  expect(JSON.stringify(data)).not.toContain("Synthetic organizational work");
  return data.results[0];
}

let patient = 8;
for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  const id = ++patient;
  test(`notice ${language} ${mobile ? "mobile" : "desktop"}: feed to participation and reply`, async ({ page, browser }, info) => {
    test.setTimeout(120_000);
    const t = dictionaries[language];
    const viewport = mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 };
    await page.setViewportSize(viewport);
    const item = await invite(page, id);
    const token = await login(page, "medical-transfer-recipient@example.test", language);
    const notice = await latestNotice(page, token);
    await page.goto("/app/notifications");
    await page.getByTestId("notification-feed-row").first().getByRole("button").first().click();
    await page.locator(`a[href="${notice.action_url}"]`).click();
    const workspace = page.getByTestId("participation-notification");
    await expect(workspace).toContainText(`Synthetic clinical patient ${id}`);
    await expect(workspace).toContainText(t["medical.participation.initiator"]);
    await expect(workspace).toContainText("Synthetic organizational work");
    await expect(workspace.locator("time")).toHaveAttribute("datetime", "2026-12-01");
    await expect(workspace.locator("time")).toHaveText(language === "kk" ? "2026-12-01" : language === "en" ? "1 December 2026" : "1 декабря 2026 г.");
    await expect(workspace.getByRole("heading")).toBeFocused();
    await workspace.screenshot({ path: info.outputPath("notice-pending.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="participation-notification"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    const keys: string[] = [];
    await page.route(`**/api/medical/participations/${item.id}/respond/`, async route => {
      keys.push(route.request().headers()["idempotency-key"]);
      if (keys.length === 1) await route.fulfill({ status: 503, json: { detail: "Synthetic outage" } });
      else await route.continue();
    });
    const decision = "decline";
    const state = "declined";
    const button = workspace.getByRole("button", { name: t[`medical.participation.${decision}`], exact: true });
    await button.click();
    const form = page.getByTestId("participation-decline-form");
    const reason = form.getByRole("textbox", { name: t["medical.participation.declineReason"] });
    await expect(reason).toBeFocused();
    await expect(form.getByRole("button", { name: t["medical.participation.decline"], exact: true })).toBeDisabled();
    await reason.fill("Synthetic private decline reason\n" + "A".repeat(150));
    await form.screenshot({ path: info.outputPath("decline-form.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="participation-decline-form"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await button.click();
    await expect(workspace.getByRole("alert")).toContainText(t["actions.errorTemporary"]);
    await expect(reason).toHaveValue("Synthetic private decline reason\n" + "A".repeat(150));
    await expect(workspace).toContainText(`Synthetic clinical patient ${id}`);
    await button.click();
    await expect(workspace).toContainText(t[`medical.participation.state.${state}`]);
    await expect(workspace.getByRole("heading")).toBeFocused();
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await workspace.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    await expect(page.getByTestId(`participation-row-${item.id}`)).toContainText(t[`medical.participation.state.${state}`]);
    await page.keyboard.press("Escape");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const senderContext = await browser.newContext({ viewport, baseURL: process.env.E2E_BASE_URL });
    try {
      const sender = await senderContext.newPage();
      const senderToken = await login(sender, "medical-role-doctor@example.test", language);
      const reply = await latestNotice(sender, senderToken);
      await sender.goto("/app/notifications");
      await sender.getByTestId("notification-feed-row").first().getByRole("button").first().click();
      await sender.locator(`a[href="${reply.action_url}"]`).click();
      const replyWorkspace = sender.getByTestId("participation-notification");
      await expect(replyWorkspace).toContainText(`Synthetic clinical patient ${id}`);
      await expect(replyWorkspace).toContainText(t[`medical.participation.state.${state}`]);
      await expect(replyWorkspace).toContainText("Synthetic private decline reason");
      await replyWorkspace.screenshot({ path: info.outputPath("notice-reply.png") });
      await replyWorkspace.getByRole("button", { name: t["medical.participation.proposals"], exact: true }).click();
      await expect(sender.getByTestId(`outgoing-${item.id}`)).toContainText(t[`medical.participation.state.${state}`]);
      await expect(sender.getByTestId(`outgoing-${item.id}`)).toContainText("Synthetic private decline reason");
      await sender.keyboard.press("Escape");
    } finally { await senderContext.close(); }
    expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic clinical patient");
  });
}

test("notice mobile: loading recovery, real conflict, revoked access and missing notice", async ({ page }, info) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });
  const item = await invite(page, 2);
  const token = await login(page, "medical-transfer-recipient@example.test", "ru");
  const notice = await latestNotice(page, token);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const routePath = "**/api/medical/participations/notification-context/**";
  await page.route(routePath, async route => { await gate; await route.fulfill({ status: 503, json: { detail: "Synthetic outage" } }); });
  await page.goto(notice.action_url);
  const workspace = page.getByTestId("participation-notification");
  try { await expect(workspace.getByRole("status", { name: ru["common.loadingData"] })).toBeVisible(); }
  finally { release(); }
  await expect(workspace.getByRole("alert")).toContainText(ru["actions.errorTemporary"]);
  await page.unroute(routePath);
  await workspace.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(workspace).toContainText("Synthetic clinical patient 2");
  const accepted = await page.request.post(`${api}/api/medical/participations/${item.id}/respond/`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": "notice-concurrent-accept" },
    data: { business_id: 1, patient_id: 2, expected_revision: 1, decision: "accept" },
  });
  expect(accepted.status()).toBe(200);
  await workspace.getByRole("button", { name: ru["medical.participation.decline"], exact: true }).click();
  const decline = page.getByTestId("participation-decline-form");
  await decline.getByRole("textbox").fill("Synthetic private decline reason");
  await decline.getByRole("button", { name: ru["medical.participation.decline"], exact: true }).click();
  await expect(workspace.getByRole("alert")).toContainText(ru["medical.clinical.conflict"]);
  await expect(decline.getByRole("button", { name: ru["medical.participation.decline"], exact: true })).toBeDisabled();
  await workspace.screenshot({ path: info.outputPath("notice-conflict.png") });
  page.once("dialog", dialog => dialog.accept());
  await decline.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  await expect(workspace).toContainText(ru["medical.participation.state.active"]);
  try {
    execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env });
    await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
    await expect(workspace).toContainText(ru["medical.notifications.unavailable"]);
    await expect(workspace).not.toContainText("Synthetic clinical patient");
    await workspace.screenshot({ path: info.outputPath("notice-denied.png") });
  } finally { execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore"], { env: process.env }); }
  await page.goto("/app/medical/participations?notification=999999");
  await expect(workspace).toContainText(ru["medical.notifications.unavailable"]);
  await page.goto("/app/medical/participations?notification=invalid");
  await expect(workspace).toContainText(ru["medical.notifications.unavailable"]);
});

test("notice mobile: long name and workspace result refresh on close", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const item = await invite(page, 3);
  const token = await login(page, "medical-transfer-recipient@example.test", "ru");
  const notice = await latestNotice(page, token);
  const longName = "Synthetic clinical patient 3 " + "A".repeat(180);
  await page.route("**/api/medical/participations/notification-context/**", async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.participation.patient_name = longName;
    await route.fulfill({ response, json: data });
  });
  await page.goto(notice.action_url);
  const workspace = page.getByTestId("participation-notification");
  await expect(workspace.getByRole("heading")).toHaveText(longName);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await workspace.screenshot({ path: info.outputPath("notice-long-name.png") });
  await page.unroute("**/api/medical/participations/notification-context/**");
  await workspace.getByRole("button", { name: ru["medical.participation.title"], exact: true }).click();
  const row = page.getByTestId(`participation-row-${item.id}`);
  await row.getByRole("button", { name: ru["medical.participation.accept"], exact: true }).click();
  await expect(row).toContainText(ru["medical.participation.state.active"]);
  await page.keyboard.press("Escape");
  await expect(workspace).toContainText(ru["medical.participation.state.active"]);
  await expect(workspace.getByRole("heading")).toHaveText("Synthetic clinical patient 3");
  await expect(workspace.getByRole("heading")).toBeFocused();
  await workspace.screenshot({ path: info.outputPath("notice-workspace-updated.png") });
  await workspace.getByRole("button", { name: ru["header.notifications"], exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/app\/notifications$/);
});

test("notice mobile: decline cancellation preserves input and role denial clears it", async ({ page }, info) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await invite(page, 4);
  const token = await login(page, "medical-transfer-recipient@example.test", "ru");
  const notice = await latestNotice(page, token);
  await page.goto(notice.action_url);
  const workspace = page.getByTestId("participation-notification");
  await workspace.getByRole("button", { name: ru["medical.participation.decline"], exact: true }).click();
  const form = page.getByTestId("participation-decline-form");
  const field = form.getByRole("textbox");
  await field.fill("Synthetic preserved refusal");
  page.once("dialog", dialog => dialog.dismiss());
  await form.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(field).toHaveValue("Synthetic preserved refusal");
  page.once("dialog", dialog => dialog.accept());
  await form.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(form).not.toBeVisible();
  await expect(workspace.getByRole("heading")).toBeFocused();
  await workspace.getByRole("button", { name: ru["medical.participation.decline"], exact: true }).click();
  await expect(field).toHaveValue("");
  await field.fill("Synthetic revoked refusal");
  try {
    execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env });
    await form.getByRole("button", { name: ru["medical.participation.decline"], exact: true }).click();
    await expect(workspace).toContainText(ru["medical.notifications.unavailable"]);
    await expect(workspace).not.toContainText("Synthetic clinical patient");
    await expect(form).not.toBeVisible();
    await workspace.screenshot({ path: info.outputPath("decline-denied.png") });
  } finally { execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore"], { env: process.env }); }
});
