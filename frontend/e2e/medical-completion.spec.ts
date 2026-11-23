import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { kk } from "../src/lib/i18n/kk";
import { ru } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { openClinicalWorkspace } from "./clinical-card-navigation";

requireIsolatedEnvironment();
const clinicalFields = ["complaints", "anamnesis", "allergies", "contraindications", "examination", "diagnosis", "procedures", "plan", "epicrisis"] as const;
for (const mode of ["ru", "kk", "denied"] as const) test(`doctor completes encounter ${mode}: missing criteria, saved content, desktop mobile and recovery`, async ({ page }, info) => {
  const t = mode === "kk" ? kk : ru;
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("completion-prepare").trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(language => localStorage.setItem("ai_smb_language", language), mode === "kk" ? "kk" : "ru");
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(entry.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(response => response.url().includes("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  const appointment = await (await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,
    { headers: { Authorization: `Bearer ${token}` } })).json();
  await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.completion.title"], exact: true }).click();
  const completion = workspace.getByTestId("encounter-completion");
  await expect(completion).toContainText(t["medical.completion.missing"]);
  await expect(completion.getByRole("button", { name: t["medical.completion.confirm"], exact: true })).toHaveCount(0);
  await completion.screenshot({ path: info.outputPath("completion-missing-desktop.png") });
  await completion.getByRole("button", { name: t["medical.completion.back"], exact: true }).click();
  await expect(workspace.getByRole("button", { name: t["medical.completion.title"], exact: true })).toBeFocused();
  for (const field of clinicalFields) await workspace.getByRole("textbox", { name: t[`medical.clinical.${field}`], exact: true }).fill(`Synthetic ${field} ${entry.appointment_id}`);
  await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
  await expect(workspace.getByRole("button", { name: t["medical.completion.title"], exact: true })).toBeEnabled();
  await workspace.getByRole("button", { name: t["medical.completion.title"], exact: true }).click();
  await expect(completion).toContainText(t["medical.completion.ready"]);
  const reason = completion.getByRole("textbox", { name: t["medical.completion.earlyReason"], exact: true });
  await reason.fill(`Synthetic completion ${entry.appointment_id}`);
  await completion.screenshot({ path: info.outputPath("completion-ready-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await completion.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("completion-mobile.png") });
  await page.route("**/encounters/*/complete/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  const confirm = completion.getByRole("button", { name: t["medical.completion.confirm"], exact: true });
  await confirm.focus(); await page.keyboard.press("Enter");
  await expect(completion.getByRole("alert")).toBeVisible();
  await expect(reason).toHaveValue(`Synthetic completion ${entry.appointment_id}`);
  await page.unroute("**/encounters/*/complete/");
  if (mode === "denied") {
    await page.route("**/encounters/*/complete/", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked access" } }));
    await confirm.click();
    await expect(completion).toHaveCount(0);
    await expect(workspace).toContainText(t["medical.denied"]);
    await expect(page.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toHaveCount(0);
    return;
  }
  if (mode === "kk") {
    await page.route("**/encounters/*/complete/", route => route.fulfill({ status: 409, json: { detail: "Synthetic changed encounter" } }));
    await confirm.click();
    await expect(confirm).toBeDisabled();
    await page.unroute("**/encounters/*/complete/");
    await completion.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(confirm).toBeEnabled();
    await expect(reason).toHaveValue(`Synthetic completion ${entry.appointment_id}`);
  }
  await confirm.click();
  await expect(page.getByTestId("encounter-completed")).toBeVisible();
  await expect(page.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: t["appointment.actionConfirm"], exact: true })).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("completed-mobile.png") });
});
