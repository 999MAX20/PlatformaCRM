import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
const dictionaries = { ru, kk, en };
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

let appointmentId = 8;
for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  const id = ++appointmentId;
  test(`proposal ${language} ${mobile ? "mobile" : "desktop"}: cross-branch invitation and outgoing`, async ({ page, browser }, info) => {
    test.setTimeout(120_000);
    const t = dictionaries[language];
    const viewport = mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 };
    await page.setViewportSize(viewport);
    const token = await login(page, "medical-role-doctor@example.test", language);
    const auth = { Authorization: `Bearer ${token}` };
    const appointment = await (await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${id}/`, { headers: auth })).json();
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    const entry = page.getByTestId("clinical-appointment-entry");
    const trigger = entry.getByRole("button", { name: t["medical.participation.proposals"], exact: true });
    await trigger.click();
    const workspace = page.getByTestId("source-proposal-workspace");
    await expect(workspace).toContainText(t["medical.participation.noOutgoing"]);
    await workspace.getByRole("button", { name: t["medical.participation.invite"], exact: true }).click();
    const branch = workspace.getByRole("combobox", { name: new RegExp(`^${t["medical.branch"]}(?:\\s|$)`) });
    await branch.click();
    await page.getByRole("option", { name: "Second", exact: true }).click();
    const form = workspace.getByTestId("participation-command-form");
    await form.getByRole("combobox", { name: new RegExp(`^${t["medical.participation.doctor"]}(?:\\s|$)`) }).click();
    await page.getByRole("option", { name: "Synthetic second-branch clinician", exact: true }).click();
    const reason = form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true });
    await reason.fill(`Synthetic handoff ${language} ${mobile}`);
    const direction = form.getByRole("textbox", { name: t["medical.participation.workDirection"], exact: true });
    const plannedDate = form.getByLabel(t["medical.participation.plannedWorkDate"], { exact: true });
    await expect(form.getByRole("button", { name: t["medical.participation.invite"], exact: true })).toBeDisabled();
    await direction.fill("Synthetic organizational work\n" + "A".repeat(140));
    await plannedDate.fill("2026-12-01");
    page.once("dialog", dialog => dialog.dismiss());
    await page.keyboard.press("Escape");
    await expect(reason).toHaveValue(`Synthetic handoff ${language} ${mobile}`);
    await branch.click();
    page.once("dialog", dialog => dialog.dismiss());
    await page.getByRole("option", { name: "First", exact: true }).click();
    await expect(branch).toContainText("Second");
    const keys: string[] = [];
    await page.route("**/api/medical/participations/", async route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      if (keys.length === 1) await route.fulfill({ status: 503, json: { detail: "Synthetic outage" } });
      else await route.continue();
    });
    const save = form.getByRole("button", { name: t["medical.participation.invite"], exact: true });
    await save.click();
    await expect(form.getByRole("alert")).toContainText(t["actions.errorTemporary"]);
    await expect(direction).toHaveValue("Synthetic organizational work\n" + "A".repeat(140));
    await expect(plannedDate).toHaveValue("2026-12-01");
    await expect(reason).toHaveValue(`Synthetic handoff ${language} ${mobile}`);
    await workspace.screenshot({ path: info.outputPath("proposal-recovery.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="source-proposal-workspace"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    const created = page.waitForResponse(r => r.url().endsWith("/api/medical/participations/") && r.request().method() === "POST");
    await save.click();
    const response = await created;
    expect(response.status()).toBe(201);
    const item = await response.json();
    const outgoing = workspace.getByTestId(`outgoing-${item.id}`);
    await expect(outgoing).toContainText(t["medical.participation.state.pending"]);
    await expect(workspace.getByRole("button", { name: t["medical.participation.invite"], exact: true })).toBeFocused();
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (language === "ru" && !mobile) {
      const receiverContext = await browser.newContext({ viewport, baseURL: process.env.E2E_BASE_URL });
      try {
        const receiver = await receiverContext.newPage();
        const receiverToken = await login(receiver, "medical-transfer-recipient@example.test", language);
        const clinicalUrl = `${process.env.E2E_API_BASE_URL}/api/medical/encounters/workspace/?business_id=1&patient_id=${id}&participation_id=${item.id}`;
        expect((await receiver.request.get(clinicalUrl, { headers: { Authorization: `Bearer ${receiverToken}` } })).status()).toBe(403);
        await receiver.goto("/app/calendar");
        await receiver.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
        const row = receiver.getByTestId(`participation-row-${item.id}`);
        await expect(row).toContainText("Synthetic organizational work");
        await expect(row).toContainText("Synthetic clinician");
        await expect(row.locator("time")).toHaveAttribute("datetime", "2026-12-01");
        await row.screenshot({ path: info.outputPath("invitation-recipient.png") });
        await row.getByRole("button", { name: t["medical.participation.accept"], exact: true }).click();
        await expect(row).toContainText(t["medical.participation.state.active"]);
        expect((await receiver.request.get(clinicalUrl, { headers: { Authorization: `Bearer ${receiverToken}` } })).status()).toBe(200);
        await row.getByRole("button", { name: t["medical.participation.proposals"], exact: true }).click();
        const reverse = receiver.getByTestId("source-proposal-workspace");
        await reverse.getByRole("button", { name: t["medical.participation.invite"], exact: true }).click();
        await reverse.getByRole("combobox", { name: new RegExp(`^${t["medical.branch"]}(?:\\s|$)`) }).click();
        await receiver.getByRole("option", { name: "First", exact: true }).click();
        await reverse.getByRole("combobox", { name: new RegExp(`^${t["medical.participation.doctor"]}(?:\\s|$)`) }).click();
        await receiver.getByRole("option", { name: "Synthetic clinician", exact: true }).click();
        await reverse.getByRole("textbox", { name: t["medical.participation.workDirection"], exact: true }).fill("Synthetic follow-up work");
        await reverse.getByLabel(t["medical.participation.plannedWorkDate"], { exact: true }).fill("2026-12-02");
        await reverse.getByRole("button", { name: t["medical.participation.invite"], exact: true }).click();
        await reverse.getByRole("button", { name: t["medical.participation.withdraw"], exact: true }).click();
        await expect(reverse).toContainText(t["medical.participation.state.withdrawn"]);
        await reverse.getByRole("button", { name: t["common.back"], exact: true }).click();
        await expect(row).toBeFocused();
        await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
        await expect(outgoing).toContainText(t["medical.participation.state.active"]);
        expect((await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/encounters/appointment-context/?business_id=1&appointment_id=${id}`, { headers: auth })).status()).toBe(200);
      } finally { await receiverContext.close(); }
    } else {
      await outgoing.getByRole("button", { name: t["medical.participation.withdraw"], exact: true }).click();
      await expect(outgoing).toContainText(t["medical.participation.state.withdrawn"]);
      await expect(outgoing).toBeFocused();
    }
    await workspace.screenshot({ path: info.outputPath("proposal-outgoing.png") });
    await page.keyboard.press("Escape");
    await expect(workspace).toHaveCount(0);
    await expect(trigger).toBeFocused();
    expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic handoff");
  });
}

test("proposal mobile: loading, read recovery and actual role revocation", async ({ page }, info) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });
  const token = await login(page, "medical-role-doctor@example.test", "ru");
  const appointment = await (await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/8/`, { headers: { Authorization: `Bearer ${token}` } })).json();
  await page.goto(`/app/calendar?appointment=8&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await page.getByTestId("clinical-appointment-entry").getByRole("button", { name: ru["medical.participation.proposals"], exact: true }).click();
  const workspace = page.getByTestId("source-proposal-workspace");
  await expect(workspace).toContainText(ru["medical.participation.noOutgoing"]);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/medical/participations/outgoing/**", async route => {
    await gate;
    await route.fulfill({ status: 503, json: { detail: "Synthetic read outage" } });
  });
  await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  try { await expect(workspace.getByRole("status", { name: ru["common.loadingData"] })).toBeVisible(); }
  finally { release(); }
  await expect(workspace.getByRole("alert")).toContainText(ru["actions.errorTemporary"]);
  await page.unroute("**/api/medical/participations/outgoing/**");
  await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  await expect(workspace).toContainText(ru["medical.participation.noOutgoing"]);
  await workspace.getByRole("button", { name: ru["medical.participation.invite"], exact: true }).click();
  await workspace.getByRole("combobox", { name: ru["medical.branch"] }).click();
  await page.getByRole("option", { name: "Second", exact: true }).click();
  await workspace.getByRole("combobox", { name: ru["medical.participation.doctor"] }).click();
  await page.getByRole("option", { name: "Synthetic second-branch clinician", exact: true }).click();
  const reason = workspace.getByRole("textbox", { name: ru["medical.participation.reason"], exact: true });
  await reason.fill("Synthetic concurrent proposal");
  await workspace.getByRole("textbox", { name: ru["medical.participation.workDirection"], exact: true }).fill("Synthetic organizational work");
  await workspace.getByLabel(ru["medical.participation.plannedWorkDate"], { exact: true }).fill("2026-12-01");
  const headers = { Authorization: `Bearer ${token}` };
  const scope = { business_id: 1, patient_id: 8, branch_id: 2, source_appointment_id: 8 };
  const candidates = await (await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/participations/candidates/`, { headers, params: scope })).json();
  const created = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/participations/`, {
    headers: { ...headers, "Idempotency-Key": "synthetic-concurrent-proposal" },
    data: { ...scope, target_member_id: candidates.results[0].member_id, expected_patient_revision: candidates.patient_revision,
      work_direction: "Synthetic organizational work", planned_work_date: "2026-12-01" },
  });
  expect(created.status()).toBe(201);
  const item = await created.json();
  await workspace.getByRole("button", { name: ru["medical.participation.invite"], exact: true }).click();
  await expect(workspace.getByRole("alert")).toContainText(ru["medical.clinical.conflict"]);
  await expect(reason).toHaveValue("Synthetic concurrent proposal");
  await expect(reason).toHaveAttribute("readonly", "");
  await workspace.screenshot({ path: info.outputPath("proposal-conflict.png") });
  page.once("dialog", dialog => dialog.accept());
  await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  const row = workspace.getByTestId(`outgoing-${item.id}`);
  await expect(row).toContainText(ru["medical.participation.state.pending"]);
  expect((await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/participations/${item.id}/withdraw/`, {
    headers: { ...headers, "Idempotency-Key": "synthetic-concurrent-withdraw" },
    data: { business_id: 1, patient_id: 8, expected_revision: item.revision },
  })).status()).toBe(200);
  await row.getByRole("button", { name: ru["medical.participation.withdraw"], exact: true }).click();
  await expect(workspace.getByRole("alert")).toContainText(ru["medical.clinical.conflict"]);
  await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  await expect(row).toContainText(ru["medical.participation.state.withdrawn"]);
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await workspace.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  await expect(workspace).toHaveCount(0);
  await expect(page.getByRole("dialog", { name: ru["medical.participation.proposals"], exact: true }).getByRole("alert")).toContainText(ru["medical.denied"]);
  await page.getByRole("dialog", { name: ru["medical.participation.proposals"], exact: true }).screenshot({ path: info.outputPath("proposal-denied.png") });
});
