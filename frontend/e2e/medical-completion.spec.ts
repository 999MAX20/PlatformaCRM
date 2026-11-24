import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { kk } from "../src/lib/i18n/kk";
import { ru } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { openClinicalWorkspace } from "./clinical-card-navigation";

requireIsolatedEnvironment();
const clinicalFields = ["complaints", "anamnesis", "allergies", "contraindications", "examination", "diagnosis", "procedures", "plan", "epicrisis"] as const;
for (const mode of ["ru", "kk", "denied", "core"] as const) test(`doctor completes encounter ${mode}: missing criteria, saved content, desktop mobile and recovery`, async ({ page, browser }, info) => {
  if (mode === "core") test.setTimeout(180_000);
  const t = mode === "kk" ? kk : ru;
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("completion-prepare", mode).trim().split(/\r?\n/).at(-1)!);
  let followUpId = 0;
  let followUpDate = "";
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
  if (mode === "core") {
    const steps = workspace.getByTestId("clinical-plan-steps");
    await steps.getByRole("button", { name: t["medical.plan.addStep"], exact: true }).click();
    await steps.getByRole("textbox").fill(`Synthetic follow-up plan ${entry.appointment_id}`);
    await steps.getByTestId("clinical-plan-teeth").getByRole("combobox").click();
    await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 11`, exact: true }).click();
  }
  await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
  await expect(workspace.getByRole("button", { name: t["medical.completion.title"], exact: true })).toBeEnabled();
  if (mode === "core") {
    await workspace.getByRole("button", { name: t["medical.reception.request"], exact: true }).click();
    const followUp = page.getByTestId("clinical-follow-up");
    const date = new Date(appointment.start_at); date.setUTCDate(date.getUTCDate() + 7);
    followUpDate = date.toISOString().slice(0, 10);
    await followUp.getByLabel(t["medical.reception.from"], { exact: true }).fill(followUpDate);
    await followUp.getByLabel(t["medical.reception.until"], { exact: true }).fill(followUpDate);
    const sent = page.waitForResponse(r => r.url().endsWith("/api/reception/booking-requests/") && r.request().method() === "POST");
    await followUp.getByRole("button", { name: t["medical.reception.send"], exact: true }).click();
    const response = await sent;
    expect(response.status()).toBe(201);
    followUpId = (await response.json()).id;
    await followUp.getByRole("button", { name: t["common.back"], exact: true }).click();
  }
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
  if (mode === "core") {
    const receptionist = JSON.parse(fixture("reception-new-member", String(entry.appointment_id), "core").trim().split(/\r?\n/).at(-1)!);
    const receptionContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const reception = await receptionContext.newPage();
    try {
      await reception.goto(`${process.env.E2E_BASE_URL}/login`);
      await reception.locator('input[name="email"]').fill(receptionist.email);
      await reception.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const loginResponse = reception.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await reception.locator('form button[type="submit"]').click();
      const receptionHeaders = { Authorization: `Bearer ${(await (await loginResponse).json()).access}` };
      await expect(reception).toHaveURL(/\/app\//);
      const api = process.env.E2E_API_BASE_URL!;
      const denied = await reception.request.get(`${api}/api/medical/encounters/appointment-context/`, {
        headers: receptionHeaders, params: { business_id: appointment.business, appointment_id: entry.appointment_id },
      });
      expect(denied.status()).toBe(403);
      await reception.getByTestId("desktop-sidebar").getByRole("link", { name: t["medical.reception.queue"], exact: true }).click();
      const row = reception.getByTestId(`reception-request-${followUpId}`);
      await expect(reception.getByTestId("reception-queue")).not.toContainText(`Synthetic follow-up plan ${entry.appointment_id}`);
      await row.getByRole("button", { name: t["medical.reception.claim"], exact: true }).click();
      await row.getByRole("button", { name: t["medical.reception.book"], exact: true }).click();
      const booking = reception.getByTestId("reception-booking");
      await booking.getByLabel(t["appointment.date"], { exact: true }).fill(followUpDate);
      await booking.getByRole("combobox", { name: new RegExp(`^${t["appointment.slot"]}`) }).click();
      await reception.getByRole("option").filter({ hasText: /^\d{1,2}:\d{2}/ }).first().click();
      await reception.setViewportSize({ width: 390, height: 844 });
      await booking.getByTestId("appointment-submit").evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
      await reception.screenshot({ path: info.outputPath("core-follow-up-mobile.png") });
      reception.once("dialog", dialog => dialog.accept());
      const bookedResponse = reception.waitForResponse(r => r.url().endsWith(`/api/reception/booking-requests/${followUpId}/book/`));
      await booking.getByTestId("appointment-submit").click();
      const booked = await bookedResponse;
      expect(booked.status()).toBe(200);
      await expect(row).toContainText(t["medical.reception.state.booked"]);
      const result = await booked.json();
      const nextId = result.appointment_id;
      const next = await page.request.get(`${api}/api/medical/encounters/appointment-context/`, {
        headers: { Authorization: `Bearer ${token}` }, params: { business_id: appointment.business, appointment_id: nextId },
      });
      expect(next.status()).toBe(200);
      const nextContext = await next.json();
      expect(nextContext.patient.client_id).toBe(entry.client_id);
      await page.goto(`/app/calendar?appointment=${nextId}&date=${followUpDate}`);
      await openClinicalWorkspace(page);
      await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
      await workspace.getByTestId("clinical-history").locator("button[aria-pressed]").first().click();
      const version = workspace.getByTestId("clinical-version");
      await expect(version).toContainText(`Synthetic follow-up plan ${entry.appointment_id}`);
      await expect(version).toContainText(`Synthetic examination ${entry.appointment_id}`);
      await version.getByTestId("clinical-plan-history").evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
      await page.screenshot({ path: info.outputPath("core-next-visit-history-mobile.png") });
    } finally { await receptionContext.close(); }
  }
});
