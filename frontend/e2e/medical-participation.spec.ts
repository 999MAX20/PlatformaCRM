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

let patientId = 1;
for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  const patient = ++patientId;
  test(`participation ${language} ${mobile ? "mobile" : "desktop"}: invite accept read and end`, async ({ page, browser }, info) => {
    test.setTimeout(120_000);
    const t = dictionaries[language];
    const viewport = mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 };
    await page.setViewportSize(viewport);
    await login(page, "medical-participation-head@example.test", language);
    await page.goto(`/app/clients/${patient}`);
    const profile = page.getByTestId("patient-administration");
    const branch = profile.getByRole("combobox", { name: t["medical.branch"] });
    await expect(branch).toBeVisible();
    await branch.click();
    await page.getByRole("option", { name: "First", exact: true }).click();
    await profile.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    const workspace = page.getByTestId("participation-workspace");
    await workspace.getByRole("button", { name: t["medical.participation.invite"], exact: true }).click();
    const form = page.getByTestId("participation-command-form");
    await form.getByRole("combobox", { name: t["medical.participation.doctor"] }).click();
    await page.getByRole("option", { name: "Synthetic clinician", exact: true }).click();
    await form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true }).fill("Synthetic referral reason");
    page.once("dialog", dialog => dialog.dismiss());
    await page.keyboard.press("Escape");
    await expect(form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true })).toHaveValue("Synthetic referral reason");
    const created = page.waitForResponse(r => r.url().endsWith("/api/medical/participations/") && r.request().method() === "POST");
    await form.getByRole("button", { name: t["medical.participation.invite"], exact: true }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    const participation = await response.json();
    const headRow = page.getByTestId(`participation-row-${participation.id}`);
    await expect(headRow).toContainText(t["medical.participation.state.pending"]);
    const doctorContext = await browser.newContext({ viewport, baseURL: process.env.E2E_BASE_URL });
    try {
      const doctor = await doctorContext.newPage();
      const token = await login(doctor, "medical-role-doctor@example.test", language);
      const clinicalUrl = `${process.env.E2E_API_BASE_URL}/api/medical/encounters/workspace/?business_id=1&patient_id=${patient}&participation_id=${participation.id}`;
      expect((await doctor.request.get(clinicalUrl, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(403);
      await doctor.goto("/app/calendar");
      await doctor.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
      const row = doctor.getByTestId(`participation-row-${participation.id}`);
      await expect(row).toContainText(t["medical.participation.state.pending"]);
      await doctor.getByRole("dialog").screenshot({ path: info.outputPath("invitation.png") });
      await row.getByRole("button", { name: t["medical.participation.accept"], exact: true }).click();
      await expect(row).toContainText(t["medical.participation.state.active"]);
      await row.getByRole("button", { name: t["medical.clinical.history"], exact: true }).click();
      await expect(doctor.getByTestId("clinical-history")).toBeVisible();
      expect((await doctor.request.get(clinicalUrl, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(200);
      await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await headRow.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
      await form.getByRole("combobox", { name: t["medical.participation.responsible"] }).click();
      await page.getByRole("option", { name: "Synthetic medical head", exact: true }).click();
      const reason = form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true });
      await reason.fill("Synthetic remaining-work responsibility");
      const keys: string[] = [];
      await page.route(`**/api/medical/participations/${participation.id}/end-by-head/`, async route => {
        keys.push(route.request().headers()["idempotency-key"]);
        if (keys.length === 1) await route.fulfill({ status: 503, json: { detail: "Synthetic temporary outage" } });
        else await route.continue();
      });
      await form.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
      await expect(form.getByRole("alert")).toContainText(t["actions.errorTemporary"]);
      await expect(reason).toHaveValue("Synthetic remaining-work responsibility");
      await page.getByRole("dialog").screenshot({ path: info.outputPath("closure-recovery.png") });
      expect((await new AxeBuilder({ page }).include('[data-testid="participation-command-form"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await form.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
      await expect(headRow).toContainText(t["medical.participation.state.ended"]);
      expect(keys.length).toBe(2);
      expect(keys[0]).toBe(keys[1]);
      expect((await doctor.request.get(clinicalUrl, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(403);
      await doctor.getByTestId("participation-workspace").getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(row).toContainText(t["medical.participation.state.ended"]);
      await expect(row.getByRole("button", { name: t["medical.clinical.history"], exact: true })).toHaveCount(0);
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toHaveCount(0);
      await expect(profile.getByRole("button", { name: t["medical.participation.title"], exact: true })).toBeFocused();
      expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic remaining-work responsibility");
    } finally { await doctorContext.close(); }
  });
}

test("participation mobile: decline, withdraw, concurrent end and current role revocation", async ({ page, browser }, info) => {
  test.setTimeout(120_000);
  const t = en;
  await page.setViewportSize({ width: 390, height: 844 });
  const headToken = await login(page, "medical-participation-head@example.test", "en");
  const headers = { Authorization: `Bearer ${headToken}` };
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/participations/`;
  const candidateResponse = await page.request.get(`${root}candidates/?business_id=1&patient_id=8&branch_id=1`, { headers });
  expect(candidateResponse.status()).toBe(200);
  const candidates = await candidateResponse.json();
  const headAccess = await (await page.request.get(`${root}workspace-access/?business_id=1`, { headers })).json();
  async function propose(key: string) {
    const result = await page.request.post(root, { headers: { ...headers, "Idempotency-Key": key }, data: {
      business_id: 1, patient_id: 8, branch_id: 1, target_member_id: candidates.results[0].member_id,
      expected_patient_revision: candidates.patient_revision,
    } });
    expect(result.status()).toBe(201);
    return result.json();
  }
  const first = await propose("negative-first");
  const doctorContext = await browser.newContext({ viewport: { width: 390, height: 844 }, baseURL: process.env.E2E_BASE_URL });
  try {
    const doctor = await doctorContext.newPage();
    const doctorToken = await login(doctor, "medical-role-doctor@example.test", "en");
    await doctor.goto("/app/calendar");
    await doctor.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    const firstRow = doctor.getByTestId(`participation-row-${first.id}`);
    await firstRow.getByRole("button", { name: t["medical.participation.decline"], exact: true }).click();
    await expect(firstRow).toContainText(t["medical.participation.state.declined"]);
    const second = await propose("negative-second");
    await page.goto("/app/clients/8");
    const profile = page.getByTestId("patient-administration");
    await profile.getByRole("combobox", { name: t["medical.branch"] }).click();
    await page.getByRole("option", { name: "First", exact: true }).click();
    await profile.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    const workspace = page.getByTestId("participation-workspace");
    const secondRow = page.getByTestId(`participation-row-${second.id}`);
    await secondRow.getByRole("button", { name: t["medical.participation.withdraw"], exact: true }).click();
    await expect(secondRow).toContainText(t["medical.participation.state.withdrawn"]);
    const third = await propose("negative-third");
    const accepted = await doctor.request.post(`${root}${third.id}/respond/`, { headers: {
      Authorization: `Bearer ${doctorToken}`, "Idempotency-Key": "negative-accept" }, data: {
      business_id: 1, patient_id: 8, expected_revision: 1, decision: "accept",
    } });
    expect(accepted.status()).toBe(200);
    await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    const thirdRow = page.getByTestId(`participation-row-${third.id}`);
    await thirdRow.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
    const form = page.getByTestId("participation-command-form");
    await form.getByRole("combobox", { name: t["medical.participation.responsible"] }).click();
    await page.getByRole("option", { name: "Synthetic medical head", exact: true }).click();
    const reason = form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true });
    await reason.fill("Synthetic preserved conflict reason");
    const closed = await page.request.post(`${root}${third.id}/end-by-head/`, { headers: {
      ...headers, "Idempotency-Key": "negative-competing-end" }, data: {
      business_id: 1, patient_id: 8, expected_revision: 2, responsible_member_id: headAccess.member_id,
      reason: "Synthetic competing closure",
    } });
    expect(closed.status()).toBe(200);
    await form.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
    await expect(form.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
    await expect(reason).toHaveValue("Synthetic preserved conflict reason");
    await expect(reason).toHaveAttribute("readonly", "");
    await expect(form.getByRole("button", { name: t["medical.participation.end"], exact: true })).toBeDisabled();
    await page.getByRole("dialog").screenshot({ path: info.outputPath("conflict.png") });
    page.once("dialog", dialog => dialog.dismiss());
    await form.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(reason).toHaveValue("Synthetic preserved conflict reason");
    page.once("dialog", dialog => dialog.accept());
    await form.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(thirdRow).toContainText(t["medical.participation.state.ended"]);
    execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
    await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(workspace).not.toBeVisible();
    await expect(page.getByRole("dialog")).toContainText(t["medical.denied"]);
    await expect(page.getByRole("dialog")).not.toContainText("Synthetic clinical patient 8");
    await page.getByRole("dialog").screenshot({ path: info.outputPath("denied.png") });
  } finally { await doctorContext.close(); }
});

test("participation list: loading, read outage retry and truthful empty state", async ({ page }, info) => {
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "medical-participation-head@example.test", "en");
  await page.goto("/app/calendar");
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let fail = true;
  await page.route("**/api/medical/participations/mine/**", async route => {
    await gate;
    if (fail) await route.fulfill({ status: 503, json: { detail: "Synthetic read failure" } });
    else await route.continue();
  });
  try {
    await page.getByRole("button", { name: en["medical.participation.title"], exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText(en["common.loadingData"], { exact: true })).toBeVisible();
    release();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await dialog.screenshot({ path: info.outputPath("list-read-error.png") });
    fail = false;
    await dialog.getByRole("button", { name: en["common.retry"], exact: true }).click();
    await expect(dialog).toContainText(en["medical.participation.empty"]);
    await expect(dialog.getByRole("alert")).toHaveCount(0);
    await dialog.screenshot({ path: info.outputPath("list-empty.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  } finally { release(); }
});
