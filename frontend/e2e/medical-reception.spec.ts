import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { openClinicalWorkspace } from "./clinical-card-navigation";
import { formatDateTime } from "../src/lib/format";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { ru as t } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

requireIsolatedEnvironment();

test("ordinary CRM appointment keeps administrative tabs without clinical requests", async ({ page }, info) => {
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "ordinary-new-appointment"],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(fixture.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  const clinicalRequests: string[] = [];
  page.on("request", request => { if (request.url().includes("/medical/encounters/appointment-context/")) clinicalRequests.push(request.url()); });
  await page.goto(`/app/calendar?appointment=${fixture.appointment_id}&date=${fixture.date}&view=day`);
  await page.getByRole("button", { name: t["calendar.openCard"], exact: true }).click();
  await expect(page.getByRole("tab", { name: t["crmCard.overview"], exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tab", { name: t["medical.clinical.title"], exact: true })).toHaveCount(0);
  await page.getByRole("tab", { name: t["crmCard.timeline"], exact: true }).click();
  await expect(page.getByRole("tab", { name: t["crmCard.timeline"], exact: true })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: t["crmCard.overview"], exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText(fixture.client_name);
  await expect(page.getByRole("tabpanel", { name: t["crmCard.overview"], exact: true })).toBeVisible();
  expect(clinicalRequests).toEqual([]);
  await page.screenshot({ path: info.outputPath("ordinary-crm-overview.png") });
});

test("ordinary calendar form: reception booking to doctor card and mobile layout", async ({ page, browser }, info) => {
  const runFixture = (...args: string[]) => JSON.parse(execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", ...args], { env: process.env, windowsHide: true, encoding: "utf8" }).trim().split(/\r?\n/).at(-1)!);
  const fixture = runFixture("reception-new-appointment");
  const member = runFixture("reception-new-member", String(fixture.appointment_id));
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(member.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const headers = { Authorization: `Bearer ${(await (await login).json()).access}` };
  await expect(page).toHaveURL(/\/app\//);
  const base = process.env.E2E_API_BASE_URL!;
  const source = await (await page.request.get(`${base}/api/appointments/${fixture.appointment_id}/`, { headers })).json();
  const client = await (await page.request.get(`${base}/api/clients/${fixture.client_id}/`, { headers })).json();
  const date = new Date(source.start_at); date.setUTCDate(date.getUTCDate() + 4);
  await page.goto(`/app/calendar?date=${date.toISOString().slice(0, 10)}&branch=${source.branch}`);
  await page.getByRole("button", { name: t["calendar.newBooking"], exact: true }).first().click();
  const form = page.getByTestId("appointment-form");
  await form.getByRole("button", { name: new RegExp(`^${t["appointment.client"]} `) }).click();
  await page.getByPlaceholder(t["common.search"], { exact: true }).fill(client.full_name);
  await page.getByRole("option", { name: client.full_name, exact: true }).click();
  await form.getByRole("combobox", { name: new RegExp(`^${t["appointment.service"]}`) }).click();
  await page.getByRole("option").filter({ hasText: fixture.alternative_service }).click();
  await form.getByRole("combobox", { name: new RegExp(`^${t["appointment.resource"]}`) }).click();
  await page.getByRole("option", { name: `${fixture.service_search} specialist`, exact: true }).click();
  await form.getByLabel(t["appointment.date"], { exact: true }).fill(date.toISOString().slice(0, 10));
  await form.getByRole("combobox", { name: new RegExp(`^${t["appointment.slot"]}`) }).click();
  await page.getByRole("option").filter({ hasText: /^\d{1,2}:\d{2}/ }).first().click();
  const note = `Synthetic ordinary ${fixture.appointment_id}`;
  await form.getByRole("textbox", { name: t["appointment.notes"], exact: true }).fill(note);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await form.screenshot({ path: info.outputPath("ordinary-calendar-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await form.getByTestId("appointment-submit").scrollIntoViewIfNeeded();
  for (const control of await form.locator('input:visible, button:visible, textarea:visible').all()) {
    const bounds = await control.boundingBox();
    if (bounds) { expect(bounds.x).toBeGreaterThanOrEqual(0); expect(bounds.x + bounds.width).toBeLessThanOrEqual(390); }
  }
  await page.screenshot({ path: info.outputPath("ordinary-calendar-mobile.png") });
  const saved = page.waitForResponse(r => r.url().endsWith("/api/appointments/create-record/") && r.request().method() === "POST");
  await form.getByTestId("appointment-submit").click();
  const response = await saved;
  expect(response.status(), await response.text()).toBe(201);
  const appointment = await response.json();
  expect(appointment.client).toBe(fixture.client_id);
  expect(appointment.branch).toBe(source.branch);
  expect(appointment.notes).toBe(note);
  await expect(form).toBeHidden();
  const clinicalUrl = `${base}/api/medical/encounters/appointment-context/`;
  const denied = await page.request.get(clinicalUrl, { headers,
    params: { business_id: appointment.business, appointment_id: appointment.id } });
  expect(denied.status()).toBe(403);
  let releaseContext!: () => void;
  const pendingContext = new Promise<void>(resolve => { releaseContext = resolve; });
  await page.route("**/api/medical/encounters/appointment-context/**", async route => {
    await pendingContext; await route.continue();
  });
  await page.goto(`/app/calendar?appointment=${appointment.id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await page.getByTestId("calendar-workspace-ready").waitFor();
  await page.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).focus();
  releaseContext();
  await expect(page.getByRole("tab", { name: t["crmCard.overview"], exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tab", { name: t["crmCard.overview"], exact: true })).toBeFocused();
  await page.unroute("**/api/medical/encounters/appointment-context/**");
  await expect(page.getByRole("tab", { name: t["medical.clinical.title"], exact: true })).toHaveCount(0);
  await expect(page.getByTestId("clinical-workspace")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("core-reception-overview-mobile.png") });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: info.outputPath("core-reception-overview-desktop.png") });

  const doctorContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const doctor = await doctorContext.newPage();
  try {
    await doctor.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await doctor.goto("/login");
    await doctor.locator('input[name="email"]').fill(fixture.doctor_email);
    await doctor.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    await doctor.locator('form button[type="submit"]').click();
    await expect(doctor).toHaveURL(/\/app\//);
    await doctor.route("**/api/medical/encounters/appointment-context/**", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
    await doctor.goto(`/app/calendar?appointment=${appointment.id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await openClinicalWorkspace(doctor);
    const workspace = doctor.getByTestId("clinical-workspace");
    await expect(workspace.getByRole("alert")).toBeVisible();
    await expect(doctor.getByRole("tab", { name: t["medical.clinical.title"], exact: true })).toHaveAttribute("aria-selected", "true");
    await doctor.unroute("**/api/medical/encounters/appointment-context/**");
    await workspace.getByRole("button", { name: t["common.retry"], exact: true }).click();
    await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`CORE-${appointment.id}`);
    await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
    await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
    const complaint = `Synthetic core clinical note ${crypto.randomUUID()}`;
    await workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true }).fill(complaint);
    await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(workspace.getByText(t["common.saved"], { exact: true })).toBeVisible();
    await doctor.screenshot({ path: info.outputPath("core-doctor-calendar-desktop.png") });
    await doctor.goto(`/app/clients?client=${fixture.client_id}&tab=timeline`);
    const profile = doctor.getByRole("dialog", { name: t["common.client"], exact: true });
    await profile.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
    await profile.getByRole("combobox", { name: t["medical.branch"] }).click();
    await doctor.getByRole("option", { name: fixture.branch_name, exact: true }).click();
    const entry = doctor.getByTestId("client-clinical-entry");
    await entry.getByRole("combobox", { name: t["medical.clientEntry.appointment"] }).click();
    await doctor.getByRole("option", { name: formatDateTime(appointment.start_at, fixture.timezone, true, "ru-RU"), exact: true }).click();
    await expect(workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toHaveValue(complaint);
    await doctor.setViewportSize({ width: 390, height: 844 });
    await workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true }).scrollIntoViewIfNeeded();
    await doctor.screenshot({ path: info.outputPath("core-doctor-client-mobile.png") });
    expect(await doctor.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.reload();
    await page.getByTestId("calendar-workspace-ready").waitFor();
    await expect(page.getByRole("tab", { name: t["crmCard.overview"], exact: true })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("clinical-workspace")).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(complaint);

    await doctor.goto(`/app/calendar?appointment=${appointment.id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await openClinicalWorkspace(doctor);
    const field = workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true });
    await expect(field).toHaveValue(complaint);
    await field.fill(`${complaint} unsaved`);
    await doctor.route("**/api/medical/encounters/*/draft/", route => route.fulfill({ status: 409, json: { detail: "Synthetic stale version" } }));
    await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(workspace).toContainText(t["medical.clinical.conflict"]);
    await expect(field).toHaveValue(`${complaint} unsaved`);
    await doctor.route("**/api/medical/encounters/appointment-context/**", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked read on reload" } }));
    doctor.once("dialog", dialog => dialog.accept());
    await workspace.locator("div.sticky").getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(workspace).toContainText(t["medical.denied"]);
    await expect(field).toHaveCount(0);
    await expect(doctor.getByRole("tab", { name: t["medical.clinical.title"], exact: true })).toHaveAttribute("aria-selected", "true");
  } finally {
    await doctorContext.close();
  }
});

for (const mode of ["book", "link", "recovery", "handover", "handover_kk", "handover_en"] as const) test(`follow-up request ${mode}: desktop/mobile, retained retry and return focus`, async ({ page, browser }, info) => {
  test.setTimeout(120000);
  const language = mode === "handover_kk" ? "kk" : mode === "handover_en" ? "en" : "ru";
  const t = language === "kk" ? kk : language === "en" ? en : (await import("../src/lib/i18n/ru")).ru;
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "reception-new-appointment"],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const headers = { Authorization: `Bearer ${(await (await login).json()).access}` };
  await expect(page).toHaveURL(/\/app\//);
  const base = process.env.E2E_API_BASE_URL!;
  const appointment = await (await page.request.get(`${base}/api/appointments/${fixture.appointment_id}/`, { headers })).json();
  const context = await (await page.request.get(`${base}/api/medical/encounters/appointment-context/`,
    { headers, params: { business_id: appointment.business, appointment_id: appointment.id } })).json();
  const scope = { business_id: appointment.business, patient_id: context.patient.id };
  async function command(path: string, data: object) {
    const response = await page.request.post(base + path, { headers: { ...headers, "Idempotency-Key": crypto.randomUUID() }, data });
    expect(response.ok(), await response.text()).toBe(true); return response.json();
  }
  const record = await command("/api/medical/records/", { ...scope, appointment_id: appointment.id,
    expected_patient_revision: context.patient.revision, number: `Synthetic reception ${appointment.id}` });
  await command("/api/medical/encounters/", { ...scope, appointment_id: appointment.id, record_id: record.id,
    expected_patient_revision: context.patient.revision, expected_appointment_updated_at: context.appointment.updated_at });
  await page.goto(`/app/calendar?appointment=${appointment.id}&date=${appointment.start_at.slice(0, 10)}`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
  const entry = workspace.getByRole("button", { name: t["medical.reception.request"], exact: true });
  await entry.click();
  const form = page.getByTestId("clinical-follow-up");
  await expect(form.getByRole("combobox", { name: new RegExp(`^${t["medical.reception.service"]} `) })).not.toContainText(t["common.select"]);
  await expect(form.getByRole("combobox", { name: new RegExp(`^${t["medical.reception.staff"]} `) })).toBeEnabled();
  const service = form.getByRole("combobox", { name: new RegExp(`^${t["medical.reception.service"]} `) });
  await form.getByLabel(t["medical.reception.search.service"], { exact: true }).fill(fixture.service_search);
  await expect(service).toBeEnabled();
  await service.click();
  const alternative = page.getByRole("option", { name: fixture.alternative_service, exact: true });
  const alternativeName = await alternative.textContent();
  await alternative.click();
  page.once("dialog", dialog => dialog.dismiss());
  await form.getByRole("button", { name: t["common.back"], exact: true }).click();
  await expect(service).toContainText(alternativeName!);
  const recommended = new Date(appointment.start_at); recommended.setUTCDate(recommended.getUTCDate() + 7);
  await form.getByLabel(t["medical.reception.from"], { exact: true }).fill(recommended.toISOString().slice(0, 10));
  recommended.setUTCDate(recommended.getUTCDate() + 14);
  await form.getByLabel(t["medical.reception.until"], { exact: true }).fill(recommended.toISOString().slice(0, 10));
  const duration = form.getByLabel(t["medical.reception.duration"], { exact: true });
  await duration.fill("45");
  await form.getByLabel(t["medical.reception.onsite"], { exact: true }).check();
  await form.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("follow-up-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await form.getByRole("heading").scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("follow-up-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const back = form.getByRole("button", { name: t["common.back"], exact: true });
  page.once("dialog", dialog => dialog.dismiss()); await back.click();
  await expect(duration).toHaveValue("45");
  let fail = true;
  const keys: string[] = [];
  await page.route(url => url.pathname === "/api/reception/booking-requests/", route => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
    return route.continue();
  });
  const send = form.getByRole("button", { name: t["medical.reception.send"], exact: true });
  await send.click();
  await expect(form.getByRole("alert")).toBeVisible();
  await expect(duration).toHaveValue("45");
  await form.getByRole("alert").scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("follow-up-retry-mobile.png") });
  const sent = page.waitForResponse(r => r.url().endsWith("/api/reception/booking-requests/") && r.request().method() === "POST");
  await send.focus(); await page.keyboard.press("Enter");
  const sentResponse = await sent;
  expect(sentResponse.status()).toBe(201);
  const requestId = (await sentResponse.json()).id;
  expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
  await expect(form.getByText(t["medical.reception.sent"], { exact: true })).toBeVisible();
  await back.click(); await expect(entry).toBeFocused();
  const receptionOutput = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "reception-new-member", String(appointment.id)],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const receptionist = JSON.parse(receptionOutput.trim().split(/\r?\n/).at(-1)!);
  const receptionContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  try {
    const receptionPage = await receptionContext.newPage();
    await receptionPage.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await receptionPage.goto(`${process.env.E2E_BASE_URL}/login`);
    await receptionPage.locator('input[name="email"]').fill(receptionist.email);
    await receptionPage.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const receptionLogin = receptionPage.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await receptionPage.locator('form button[type="submit"]').click();
    const receptionHeaders = { Authorization: `Bearer ${(await (await receptionLogin).json()).access}` };
    await expect(receptionPage).toHaveURL(/\/app\//);
    await receptionPage.getByTestId("desktop-sidebar").getByRole("link", { name: t["medical.reception.queue"], exact: true }).click();
    const queue = receptionPage.getByTestId("reception-queue");
    const row = queue.getByTestId(`reception-request-${requestId}`);
    await expect(row).toContainText(context.patient.full_name);
    if (mode === "recovery") {
      const claimUrl = `**/api/reception/booking-requests/${requestId}/claim/`;
      await receptionPage.route(claimUrl, route => route.fulfill({ status: 409,
        contentType: "application/json", body: JSON.stringify({ code: "invalid_transition" }) }));
      await row.getByRole("button", { name: t["medical.reception.claim"], exact: true }).click();
      await expect(queue.getByRole("alert")).toBeVisible();
      await expect(row).toHaveCount(0);
      await receptionPage.screenshot({ path: info.outputPath("reception-claim-conflict.png") });
      await receptionPage.unroute(claimUrl);
      await queue.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(row).toContainText(context.patient.full_name);
    }
    await row.getByRole("button", { name: t["medical.reception.claim"], exact: true }).click();
    await expect(row.getByRole("button", { name: t["medical.reception.book"], exact: true })).toBeVisible();
    await receptionPage.screenshot({ path: info.outputPath("reception-queue-desktop.png") });
    await receptionPage.setViewportSize({ width: 390, height: 844 });
    await row.scrollIntoViewIfNeeded();
    await receptionPage.screenshot({ path: info.outputPath("reception-queue-mobile.png") });
    if (mode.startsWith("handover")) {
      const colleagueOutput = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "reception-new-member", String(appointment.id)],
        { env: process.env, windowsHide: true, encoding: "utf8" });
      const colleague = JSON.parse(colleagueOutput.trim().split(/\r?\n/).at(-1)!);
      await row.getByRole("button", { name: t["medical.reception.handover"], exact: true }).click();
      const panel = receptionPage.getByTestId("reception-handover");
      const recipient = panel.getByRole("combobox", { name: new RegExp(`^${t["medical.reception.recipient"]}`) });
      await recipient.click();
      await receptionPage.getByRole("option", { name: t["medical.reception.release"], exact: true }).click();
      const reason = panel.getByRole("textbox", { name: t["medical.reception.transferReason"], exact: true });
      await reason.fill(`Synthetic release ${requestId}`);
      receptionPage.once("dialog", dialog => dialog.dismiss());
      await queue.getByRole("button", { name: t["common.back"], exact: true }).click();
      await expect(reason).toHaveValue(`Synthetic release ${requestId}`);
      await receptionPage.setViewportSize({ width: 1440, height: 1000 });
      await receptionPage.mouse.move(1300, 800);
      await panel.screenshot({ path: info.outputPath("handover-desktop.png") });
      await receptionPage.setViewportSize({ width: 390, height: 844 });
      await panel.getByRole("button", { name: t["medical.reception.transfer"], exact: true }).scrollIntoViewIfNeeded();
      await receptionPage.screenshot({ path: info.outputPath("handover-mobile.png") });
      const transferUrl = `**/api/reception/booking-requests/${requestId}/transfer/`;
      if (mode === "handover_kk") {
        await receptionPage.route(transferUrl, route => route.fulfill({ status: 409,
          contentType: "application/json", body: JSON.stringify({ code: "invalid_transition" }) }));
        receptionPage.once("dialog", dialog => dialog.accept());
        await panel.getByRole("button", { name: t["medical.reception.transfer"], exact: true }).click();
        await expect(panel.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
        await expect(panel.locator("form")).toHaveCount(0);
        await receptionPage.screenshot({ path: info.outputPath("handover-conflict-mobile.png") });
        await receptionPage.unroute(transferUrl);
        receptionPage.once("dialog", dialog => dialog.accept());
        await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
        await expect(row).toBeFocused();
        await row.getByRole("button", { name: t["medical.reception.handover"], exact: true }).click();
        await recipient.click();
        await receptionPage.getByRole("option", { name: t["medical.reception.release"], exact: true }).click();
        await reason.fill(`Synthetic release ${requestId}`);
      }
      const releaseKeys: string[] = []; let loseRelease = true;
      await receptionPage.route(transferUrl, async route => {
        releaseKeys.push(route.request().headers()["idempotency-key"]);
        const response = await route.fetch();
        if (loseRelease) { loseRelease = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
        return route.fulfill({ response });
      });
      receptionPage.once("dialog", dialog => dialog.accept());
      await panel.getByRole("button", { name: t["medical.reception.transfer"], exact: true }).click();
      await expect(panel.getByRole("alert")).toBeVisible();
      await expect(reason).toHaveValue(`Synthetic release ${requestId}`);
      receptionPage.once("dialog", dialog => dialog.accept());
      await panel.getByRole("button", { name: t["medical.reception.transfer"], exact: true }).click();
      await expect(row.getByRole("button", { name: t["medical.reception.claim"], exact: true })).toBeVisible();
      expect(releaseKeys).toHaveLength(2); expect(releaseKeys[0]).toBe(releaseKeys[1]);
      await receptionPage.unroute(transferUrl);
      await row.getByRole("button", { name: t["medical.reception.claim"], exact: true }).click();
      await expect(row.getByRole("button", { name: t["medical.reception.book"], exact: true })).toBeVisible();
      await row.getByRole("button", { name: t["medical.reception.handover"], exact: true }).click();
      await panel.getByRole("textbox", { name: t["medical.reception.searchRecipient"], exact: true }).fill(colleague.name);
      await recipient.click();
      await receptionPage.getByRole("option", { name: colleague.name, exact: true }).click();
      await reason.fill(`Synthetic handover ${requestId}`);
      receptionPage.once("dialog", dialog => dialog.accept());
      await panel.getByRole("button", { name: t["medical.reception.transfer"], exact: true }).click();
      await expect(row).toContainText(colleague.name);
      await expect(row.getByRole("button", { name: t["medical.reception.book"], exact: true })).toHaveCount(0);
      await row.getByRole("button", { name: t["medical.reception.handover"], exact: true }).click();
      await expect(panel.locator("form")).toHaveCount(0);
      await expect(panel.getByTestId("reception-history")).toContainText(`Synthetic handover ${requestId}`);
      await expect(panel.getByTestId("reception-history")).toContainText(`Synthetic release ${requestId}`);
      await panel.getByTestId("reception-history").screenshot({ path: info.outputPath("handover-history-mobile.png") });
      const lastHistory = panel.getByTestId("reception-history").locator("li").last();
      await lastHistory.evaluate(element => element.scrollIntoView({ block: "center" }));
      await expect.poll(async () => {
        const item = await lastHistory.boundingBox();
        const nav = await receptionPage.getByTestId("bottom-mobile-menu-trigger").locator("..").boundingBox();
        return !!item && !!nav && item.y >= 0 && item.y + item.height <= nav.y;
      }).toBe(true);
      await receptionPage.screenshot({ path: info.outputPath("handover-history-bottom-mobile.png") });
      const receiverContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
      try {
        const receiver = await receiverContext.newPage();
        await receiver.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
        await receiver.goto(`${process.env.E2E_BASE_URL}/login`);
        await receiver.locator('input[name="email"]').fill(colleague.email);
        await receiver.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
        await receiver.locator('form button[type="submit"]').click();
        await expect(receiver).toHaveURL(/\/app\//);
        await receiver.goto(`${process.env.E2E_BASE_URL}/app/medical/reception`);
        const assigned = receiver.getByTestId(`reception-request-${requestId}`);
        await expect(assigned).toContainText(colleague.name);
        await expect(assigned.getByRole("button", { name: t["medical.reception.book"], exact: true })).toBeVisible();
        await receiver.screenshot({ path: info.outputPath("handover-recipient-mobile.png") });
        if (mode === "handover_kk") {
          await receiver.route("**/api/reception/booking-requests/*/history/**", route => route.fulfill({ status: 403,
            contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
          await assigned.getByRole("button", { name: t["medical.reception.handover"], exact: true }).click();
          await expect(receiver.getByTestId("reception-queue").getByRole("alert")).toBeVisible();
          await expect(receiver.getByTestId("reception-handover")).toHaveCount(0);
          await expect(assigned).toHaveCount(0);
          await expect(receiver.getByTestId("reception-queue")).not.toContainText(context.patient.full_name);
          await receiver.screenshot({ path: info.outputPath("handover-denied-mobile.png") });
        }
      } finally { await receiverContext.close(); }
      return;
    }
    if (mode === "book") {
    await row.getByRole("button", { name: t["medical.reception.book"], exact: true }).click();
    const booking = receptionPage.getByTestId("reception-booking");
    await expect(booking.getByRole("textbox", { name: t["appointment.client"], exact: true })).toHaveValue(context.patient.full_name);
    await expect(booking.getByRole("textbox", { name: t["appointment.notes"], exact: true })).toHaveCount(0);
    await booking.getByLabel(t["appointment.date"], { exact: true }).fill(recommended.toISOString().slice(0, 10));
    await booking.getByRole("combobox", { name: new RegExp(`^${t["appointment.slot"]}`) }).click();
    await receptionPage.getByRole("option").filter({ hasText: /^\d{1,2}:\d{2}/ }).first().click();
    await booking.getByTestId("appointment-submit").scrollIntoViewIfNeeded();
    const viewport = receptionPage.viewportSize()!;
    for (const control of await booking.locator('input:visible, button:visible').all()) {
      const bounds = await control.boundingBox();
      if (bounds) { expect(bounds.x).toBeGreaterThanOrEqual(0); expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width); }
    }
    await receptionPage.screenshot({ path: info.outputPath("reception-booking-mobile.png") });
    receptionPage.once("dialog", dialog => dialog.accept());
    const booked = receptionPage.waitForResponse(r => r.url().endsWith(`/api/reception/booking-requests/${requestId}/book/`));
    await booking.getByTestId("appointment-submit").click();
    expect((await booked).status()).toBe(200);
    } else {
      const serviceId = sentResponse.request().postDataJSON().service_id;
      const slotsResponse = await receptionPage.request.get(`${base}/api/appointments/available-slots/`, { headers: receptionHeaders,
        params: { business_id: appointment.business, branch_id: appointment.branch, service_id: serviceId,
          resource_id: appointment.resource, date: recommended.toISOString().slice(0, 10) } });
      expect(slotsResponse.ok()).toBe(true);
      const slots = await slotsResponse.json(); expect(slots.length).toBeGreaterThan(0);
      const existingResponse = await receptionPage.request.post(`${base}/api/appointments/create-record/`, {
        headers: { ...receptionHeaders, "Idempotency-Key": crypto.randomUUID() }, data: {
          business: appointment.business, client: appointment.client, service: serviceId, resource: appointment.resource,
          branch: appointment.branch, start_at: slots[0].start_at, expected_price: "100.00", expected_duration_minutes: 30,
        },
      });
      expect(existingResponse.ok(), await existingResponse.text()).toBe(true);
      const existing = await existingResponse.json();
      await row.getByRole("button", { name: t["medical.reception.link"], exact: true }).click();
      const linking = receptionPage.getByTestId("reception-existing");
      await expect(linking.getByRole("radio")).toHaveCount(1);
      await linking.getByRole("radio").check();
      receptionPage.once("dialog", dialog => dialog.dismiss());
      await queue.getByRole("button", { name: t["common.back"], exact: true }).click();
      await expect(linking.getByRole("radio")).toBeChecked();
      await receptionPage.setViewportSize({ width: 1440, height: 1000 });
      await receptionPage.screenshot({ path: info.outputPath("reception-link-desktop.png") });
      if (mode === "recovery") {
        const linkUrl = `**/api/reception/booking-requests/${requestId}/link/`;
        await receptionPage.route(linkUrl, route => route.fulfill({ status: 409,
          contentType: "application/json", body: JSON.stringify({ code: "invalid_transition" }) }));
        receptionPage.once("dialog", dialog => dialog.accept());
        await linking.getByRole("button", { name: t["medical.reception.confirm"], exact: true }).click();
        await expect(linking.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
        await expect(linking.getByRole("button", { name: t["medical.reception.confirm"], exact: true })).toHaveCount(0);
        await receptionPage.setViewportSize({ width: 390, height: 844 });
        await expect(receptionPage.getByTestId("desktop-sidebar")).toBeHidden();
        await receptionPage.screenshot({ path: info.outputPath("reception-link-conflict.png") });
        await receptionPage.unroute(linkUrl);
        receptionPage.once("dialog", dialog => dialog.accept());
        await linking.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
        await expect(row).toBeFocused();
        await row.getByRole("button", { name: t["medical.reception.link"], exact: true }).click();
        await linking.getByRole("radio").check();
      }
      let loseResponse = true;
      const linkKeys: string[] = [];
      await receptionPage.route(`**/api/reception/booking-requests/${requestId}/link/`, async route => {
        linkKeys.push(route.request().headers()["idempotency-key"]);
        const response = await route.fetch();
        if (loseResponse) { loseResponse = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
        return route.fulfill({ response });
      });
      receptionPage.once("dialog", dialog => dialog.accept());
      await linking.getByRole("button", { name: t["medical.reception.confirm"], exact: true }).click();
      await expect(linking.getByRole("alert")).toBeVisible();
      await expect(linking.getByRole("radio")).toBeChecked();
      await receptionPage.setViewportSize({ width: 390, height: 844 });
      await receptionPage.screenshot({ path: info.outputPath("reception-link-retry-mobile.png") });
      receptionPage.once("dialog", dialog => dialog.accept());
      const linked = receptionPage.waitForResponse(r => r.url().endsWith(`/api/reception/booking-requests/${requestId}/link/`));
      await linking.getByRole("button", { name: t["medical.reception.confirm"], exact: true }).click();
      const linkedResponse = await linked;
      expect(linkedResponse.status()).toBe(200);
      expect((await linkedResponse.json()).appointment_id).toBe(existing.id);
      expect(linkKeys).toHaveLength(2); expect(linkKeys[0]).toBe(linkKeys[1]);
      const appointmentsResponse = await receptionPage.request.get(`${base}/api/appointments/`, { headers: receptionHeaders,
        params: { business: appointment.business, client_ids: String(appointment.client) } });
      expect((await appointmentsResponse.json()).results).toHaveLength(2);
    }
    await expect(row).toContainText(t["medical.reception.state.booked"]);
    await expect(row).toBeFocused();
    await expect(row.getByRole("button", { name: t["medical.plan.openBooking"], exact: true })).toBeVisible();
    expect(await receptionPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.bringToFront();
    const connection = page.getByTestId("connectivity-banner");
    if (await connection.isVisible()) {
      await connection.getByRole("button", { name: t["common.retry"], exact: true }).click();
      await expect(connection).toBeHidden();
    }
    const outcome = page.getByTestId("clinical-follow-up-results");
    await outcome.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(outcome.getByTestId(`clinical-follow-up-${requestId}`)).toContainText(t["medical.reception.state.booked"]);
    await outcome.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath("doctor-follow-up-outcome-mobile.png") });
    if (mode === "recovery") {
      await page.route("**/api/reception/booking-requests/primary/**", route => route.fulfill({ status: 403,
        contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
      await outcome.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(workspace.getByRole("alert")).toBeVisible();
      await expect(workspace.getByRole("textbox")).toHaveCount(0);
      await expect(outcome).toHaveCount(0);
      await page.screenshot({ path: info.outputPath("doctor-follow-up-denied-mobile.png") });
      await receptionPage.route(url => url.pathname === "/api/reception/booking-requests/", route => route.fulfill({ status: 403,
        contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
      await queue.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(queue.getByRole("alert")).toBeVisible();
      await expect(row).toHaveCount(0);
      await expect(queue).not.toContainText(context.patient.full_name);
      await receptionPage.screenshot({ path: info.outputPath("reception-denied-mobile.png") });
    }
  } finally { await receptionContext.close(); }
});
