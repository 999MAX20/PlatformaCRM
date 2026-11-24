import { openClinicalWorkspace } from "./clinical-card-navigation";
import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();

test("assistant workspace: accept prepare and lose revoked access", async ({ page, browser }, info) => {
  test.skip(process.env.E2E_MEDICAL_FILES !== "1", "Requires isolated clinical fixtures");
  test.setTimeout(120000);
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("files-new-appointment").trim().split(/\r?\n/).at(-1)!);
  const assistant = JSON.parse(fixture("assistant-new-member", String(entry.appointment_id)).trim().split(/\r?\n/).at(-1)!);
  fixture("historical-orders-context", String(entry.appointment_id));
  const base = process.env.E2E_API_BASE_URL!;
  const authContext = await browser.newContext();
  async function login(target: typeof page, email: string) {
    await target.goto(`${process.env.E2E_BASE_URL}/login`);
    await target.locator('input[name="email"]').fill(email);
    await target.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const authentication = target.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await target.locator('form button[type="submit"]').click();
    const response = await authentication; expect(response.ok()).toBe(true);
    const token = (await response.json()).access;
    await expect(target).toHaveURL(/\/app\//); return token;
  }
  let doctorToken: string, headToken: string;
  try {
    doctorToken = await login(await authContext.newPage(), "medical-role-doctor@example.test");
    const headContext = await browser.newContext();
    try { headToken = await login(await headContext.newPage(), "medical-template-head@example.test"); }
    finally { await headContext.close(); }
  } finally { await authContext.close(); }
  const command = async (path: string, data: object, token = doctorToken) => {
    const response = await page.request.post(base + path, { headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() }, data });
    expect(response.ok(), await response.text()).toBe(true); return response.json();
  };
  const title = `Synthetic assistant document ${entry.appointment_id}`;
  const template = await command("/api/medical/document-templates/common/", { business_id: assistant.business_id, title, text: "Synthetic source {{patient.full_name}}", reason: "" }, headToken);
  await command(`/api/medical/document-templates/common/versions/${template.version_id}/submit/`, { business_id: assistant.business_id }, headToken);
  await command(`/api/medical/document-templates/versions/${template.version_id}/decision/`, { business_id: assistant.business_id, decision: "approved", reason: "Synthetic approval" }, headToken);
  const appointment = await (await page.request.get(`${base}/api/appointments/${entry.appointment_id}/`, { headers: { Authorization: `Bearer ${doctorToken}` } })).json();
  const invitation = await command("/api/medical/appointment-assistants/", { business_id: assistant.business_id, patient_id: assistant.patient_id,
    appointment_id: entry.appointment_id, target_member_id: assistant.member_id, expected_updated_at: appointment.updated_at });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await login(page, assistant.email);
  await page.getByRole("button", { name: ru["header.notifications"], exact: true }).click();
  const notification = page.getByTestId("notification-menu");
  await expect(notification.getByText(ru["medical.notifications.assistant_invited"], { exact: true })).toBeVisible();
  await expect(notification).not.toContainText("Synthetic file patient");
  await page.screenshot({ path: info.outputPath("assistant-notification-desktop.png") });
  await notification.getByText(ru["medical.notifications.assistant_invited"], { exact: true }).click();
  await expect(page).toHaveURL(/\/app\/medical\/assistants/);
  const assistantLink = page.getByTestId("desktop-sidebar").getByRole("link", { name: ru["medical.assistants.mine"], exact: true });
  await expect(assistantLink).toBeVisible();
  await assistantLink.click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: ru["sidebar.expand"], exact: true }).click();
  const mobileAssistantLink = page.getByTestId("mobile-sidebar").getByRole("link", { name: ru["medical.assistants.mine"], exact: true });
  await expect(mobileAssistantLink).toBeVisible();
  await page.screenshot({ path: info.outputPath("assistant-navigation-mobile.png") });
  await mobileAssistantLink.click();
  await expect(page.getByTestId("mobile-sidebar")).not.toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  const inbox = page.getByTestId("assistant-inbox");
  await expect(inbox).not.toContainText(`Synthetic file patient ${entry.appointment_id}`);
  await inbox.getByRole("button", { name: ru["medical.assistants.accept"], exact: true }).click();
  await inbox.getByRole("button", { name: ru["medical.assistants.open"], exact: true }).click();
  const workspace = page.getByTestId("assistant-drafts");
  const templateExportRequests: string[] = [];
  page.on("request", request => { if (/\/document-templates\/versions\/\d+\/docx-/.test(request.url())) templateExportRequests.push(request.url()); });
  await workspace.getByRole("button", { name: ru["medical.documents.create"], exact: true }).click();
  await workspace.getByRole("button", { name: new RegExp(title) }).click();
  const text = workspace.getByRole("textbox", { name: ru["medical.documents.text"], exact: true });
  await expect(text).toBeVisible();
  await expect(text).toHaveValue(/^Synthetic source Synthetic file patient /);
  expect(await text.inputValue()).not.toContain("{{patient.full_name}}");
  await expect(workspace.getByRole("button", { name: ru["medical.documents.confirmReview"], exact: true })).toHaveCount(0);
  await text.fill(`Synthetic assistant draft ${entry.appointment_id}`);
  page.once("dialog", dialog => dialog.dismiss());
  await inbox.getByRole("button", { name: ru["medical.assistants.back"], exact: true }).click();
  await expect(text).toHaveValue(`Synthetic assistant draft ${entry.appointment_id}`);
  page.once("dialog", dialog => dialog.dismiss());
  await page.getByTestId("desktop-sidebar").getByRole("link", { name: ru["nav.dashboard"], exact: true }).click();
  await expect(page).toHaveURL(/\/app\/medical\/assistants/);
  await expect(text).toHaveValue(`Synthetic assistant draft ${entry.appointment_id}`);
  await page.screenshot({ path: info.outputPath("assistant-editor-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath("assistant-editor-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const commandKeys: string[] = [];
  await page.route("**/api/medical/appointment-assistants/*/save-document/", async route => {
    commandKeys.push(route.request().headers()["idempotency-key"]);
    if (commandKeys.length === 1) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic temporary save failure" }) });
    else await route.continue();
  });
  await workspace.getByRole("button", { name: ru["medical.clinical.save"], exact: true }).click();
  await expect(workspace.getByRole("alert")).toBeVisible();
  await expect(text).toHaveValue(`Synthetic assistant draft ${entry.appointment_id}`);
  await page.screenshot({ path: info.outputPath("assistant-save-error-mobile.png") });
  const saveButton = workspace.getByRole("button", { name: ru["medical.clinical.save"], exact: true });
  await saveButton.focus();
  await expect(saveButton).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(workspace.getByText(ru["medical.assistants.saved"], { exact: true })).toBeVisible();
  expect(commandKeys).toHaveLength(2);
  expect(commandKeys[0]).toBeTruthy();
  expect(commandKeys[1]).toBe(commandKeys[0]);
  await page.unroute("**/api/medical/appointment-assistants/*/save-document/");
  await workspace.getByRole("button", { name: new RegExp(title) }).click();
  await expect(text).toHaveValue(`Synthetic assistant draft ${entry.appointment_id}`);
  await text.fill(`Synthetic corrected draft ${entry.appointment_id}`);
  await workspace.getByRole("textbox", { name: ru["medical.templates.reason"], exact: true }).fill("Synthetic correction");
  await workspace.getByRole("button", { name: ru["medical.clinical.save"], exact: true }).click();
  await expect(workspace.getByText(ru["medical.assistants.saved"], { exact: true })).toBeVisible();
  await expect(workspace.getByRole("button", { name: new RegExp(title) })).toBeEnabled();
  await workspace.getByRole("button", { name: new RegExp(title) }).click();
  await expect(text).toHaveValue(`Synthetic corrected draft ${entry.appointment_id}`);
  await workspace.getByRole("button", { name: ru["medical.documents.back"], exact: true }).click();
  await expect(workspace.getByRole("button", { name: new RegExp(title) })).toBeFocused();
  await inbox.getByRole("button", { name: ru["medical.assistants.back"], exact: true }).click();
  const reopen = inbox.getByRole("button", { name: ru["medical.assistants.open"], exact: true });
  await expect(reopen).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(workspace.getByRole("button", { name: new RegExp(title) })).toBeEnabled();
  const doctorContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  try {
    const doctor = await doctorContext.newPage();
    await doctor.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await login(doctor, "medical-role-doctor@example.test");
    await doctor.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await openClinicalWorkspace(doctor);
    await doctor.getByTestId("clinical-workspace").getByRole("tab", { name: ru["medical.documents.title"], exact: true }).click();
    const documents = doctor.getByTestId("medical-documents");
    await documents.getByRole("button", { name: new RegExp(title) }).click();
    const detail = documents.getByTestId("medical-document-detail");
    await expect(detail.getByTestId("medical-document-text")).toHaveText(`Synthetic corrected draft ${entry.appointment_id}`);
    await expect(detail).toContainText(assistant.name);
    const review = detail.getByTestId("document-review");
    await review.getByRole("button", { name: ru["medical.documents.submitReview"], exact: true }).click();
    await review.getByRole("button", { name: ru["medical.documents.confirmReview"], exact: true }).click();
    await expect(detail.getByText(ru["medical.documents.reviewed"], { exact: true })).toBeVisible();
    const pdf = detail.getByTestId("medical-document-pdf");
    await pdf.getByRole("button", { name: ru["medical.documents.pdfPreview"], exact: true }).click();
    await expect(pdf.getByRole("status")).toContainText(ru["medical.files.pending"]);
    fixture("document-artifacts-scan", String(entry.appointment_id));
    await pdf.getByRole("button", { name: ru["common.retry"], exact: true }).click();
    await expect(pdf.getByTestId("medical-pdf-text")).toContainText(`Synthetic corrected draft ${entry.appointment_id}`);
    await expect(pdf.locator("canvas")).toBeVisible();
    await pdf.scrollIntoViewIfNeeded();
    await doctor.screenshot({ path: info.outputPath("assistant-doctor-reviewed-pdf.png") });
    await doctor.evaluate(() => {
      const original = window.open.bind(window);
      window.open = (...args) => {
        const target = original(...args);
        if (target) target.print = () => { target.document.documentElement.dataset.printRequested = "true"; };
        return target;
      };
    });
    const printing = doctor.waitForEvent("popup");
    await pdf.getByRole("button", { name: ru["medical.documents.print"], exact: true }).click();
    const printPage = await printing;
    await expect(printPage.locator("html")).toHaveAttribute("data-print-requested", "true");
    await expect(printPage.locator("img")).toHaveCount(1);
    expect(await printPage.locator("img").evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 500)).toBe(true);
    await printPage.screenshot({ path: info.outputPath("assistant-doctor-print.png") });
  } finally { await doctorContext.close(); }
  await command(`/api/medical/appointment-assistants/${invitation.id}/revoke/`, { business_id: assistant.business_id, expected_revision: 2 });
  await workspace.getByRole("button", { name: new RegExp(title) }).click();
  await expect(inbox.getByRole("alert")).toContainText(ru["medical.denied"]);
  await expect(workspace).toHaveCount(0);
  await expect(inbox).not.toContainText(title);
  expect(templateExportRequests).toEqual([]);
});

test("appointment assistant management: invite and revoke inline", async ({ page }, info) => {
  test.skip(process.env.E2E_MEDICAL_FILES !== "1", "Requires isolated clinical fixtures");
  const fixture = (command: string, ...args: string[]) => JSON.parse(execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" }).trim().split(/\r?\n/).at(-1)!);
  const entry = fixture("files-new-appointment");
  const assistant = fixture("assistant-new-member", String(entry.appointment_id));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const authentication = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await authentication).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.ok()).toBe(true);
  const appointment = await response.json();
  await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const panel = page.getByTestId("appointment-assistants");
  await panel.getByRole("button", { name: ru["medical.assistants.title"], exact: true }).click();
  await panel.getByRole("button", { name: ru["medical.assistants.invite"], exact: true }).click();
  await panel.getByLabel(ru["medical.assistants.search"], { exact: true }).fill(assistant.name);
  await panel.getByRole("button", { name: ru["medical.assistants.find"], exact: true }).click();
  await panel.getByRole("button", { name: ru["medical.assistants.inviteNamed"].replace("{name}", assistant.name), exact: true }).click();
  await expect(panel.getByText(ru["medical.assistants.state.pending"], { exact: true })).toBeVisible();
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("assistant-management-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("assistant-management-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  page.once("dialog", dialog => dialog.accept());
  await panel.getByRole("button", { name: ru["medical.assistants.revokeNamed"].replace("{name}", assistant.name), exact: true }).click();
  await expect(panel.getByText(ru["medical.assistants.state.revoked"], { exact: true })).toBeVisible();
});

for (const [language, width, t] of [["kk", 1440, kk], ["en", 390, en]] as const) {
  test(`head documents ${language}: inline patient card and saved PDF`, async ({ page }, info) => {
    test.skip(process.env.E2E_MEDICAL_FILES !== "1", "Requires the isolated PDF scanner fixture");
    test.setTimeout(120000);
    const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
      ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
    const entry = JSON.parse(fixture("files-new-appointment").trim().split(/\r?\n/).at(-1)!);
    fixture("historical-orders-context", String(entry.appointment_id));
    fixture("historical-documents-populate", String(entry.appointment_id), "1", language === "kk" ? "print-long" : "short");
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-participation-head@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/app\//);
    await page.goto(`/app/clients?client=${entry.client_id}&tab=timeline`);
    const dialog = page.getByRole("dialog", { name: t["common.client"], exact: true });
    await dialog.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
    await dialog.getByLabel(t["medical.branch"], { exact: true }).click();
    const basisResponse = page.waitForResponse(r => r.url().includes("/client-appointments/") && r.request().method() === "GET");
    await page.getByRole("option", { name: "First", exact: true }).click();
    const basis = await basisResponse;
    expect(basis.status()).toBe(200);
    const branchId = new URL(basis.url()).searchParams.get("branch_id")!;
    expect((await basis.json()).head_documents).toBeTruthy();
    const documents = dialog.getByTestId("medical-documents");
    await expect(documents.getByRole("button", { name: t["medical.documents.create"], exact: true })).toHaveCount(0);
    await documents.getByRole("button", { name: /^Synthetic historical document/ }).click();
    const detail = documents.getByTestId("medical-document-detail");
    await expect(detail.getByTestId("medical-document-text")).toHaveText("Synthetic historical document 0 v2");
    await detail.getByRole("button", { name: t["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
    const originalText = "Synthetic historical document 0 v1" + (language === "kk" ? "\n" + Array.from({ length: 85 }, (_, line) => `Строка ${line}: Қазақша мәтін және русский текст.`).join("\n") : "");
    await expect(detail.getByTestId("medical-document-text")).toHaveText(originalText);
    await expect(detail.getByRole("button", { name: t["medical.documents.edit"], exact: true })).toHaveCount(0);
    const pdf = detail.getByTestId("medical-document-pdf");
    const exportHistory = pdf.getByTestId("document-export-history");
    if (language === "kk") {
      await page.route("**/export-history/**", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic history unavailable"}' }), { times: 1 });
    }
    await exportHistory.getByRole("button", { name: t["medical.documents.exportHistory"], exact: true }).click();
    if (language === "kk") {
      await expect(exportHistory.getByRole("alert")).toBeVisible();
      await exportHistory.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(exportHistory.getByText(t["medical.documents.exportHistoryEmpty"], { exact: true })).toBeVisible();
    await pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true }).click();
    await expect(pdf.getByRole("status")).toContainText(t["medical.files.pending"]);
    fixture("document-artifacts-scan", String(entry.appointment_id));
    const savedPdf = page.waitForResponse(r => /\/versions\/\d+\/pdf\//.test(r.url()) && r.request().method() === "GET");
    await pdf.getByRole("button", { name: t["common.retry"], exact: true }).click();
    const savedBytes = await (await savedPdf).body();
    await expect(pdf.getByTestId("medical-pdf-text")).toContainText("Synthetic historical document 0 v1");
    await expect(page.getByRole("dialog")).toHaveCount(1);
    await pdf.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`head-pdf-${language}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (language === "kk") {
      await page.route("**/pdf-download/", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic export unavailable"}' }), { times: 1 });
      await pdf.getByRole("button", { name: t["medical.documents.downloadPdf"], exact: true }).click();
      await expect(pdf.getByRole("alert")).toBeVisible();
      await expect(detail.getByTestId("medical-document-text")).toHaveText(originalText);
    }
    const downloading = page.waitForEvent("download");
    await pdf.getByRole("button", { name: language === "kk" ? t["common.retry"] : t["medical.documents.downloadPdf"], exact: true }).click();
    const download = await downloading;
    const downloadedPath = (await download.path())!;
    expect(readFileSync(downloadedPath)).toEqual(savedBytes);
    await expect(exportHistory.getByText(t["medical.documents.document_exported"], { exact: true })).toBeVisible();
    const pageCount = Number(execFileSync(process.env.E2E_PYTHON!, ["-c", "import sys; from pypdf import PdfReader; print(len(PdfReader(sys.argv[1]).pages))", downloadedPath], { windowsHide: true, encoding: "utf8" }).trim());
    if (language === "kk") expect(pageCount).toBeGreaterThan(1);
    if (language === "kk") {
      await page.evaluate(() => { (window as unknown as { originalOpen: typeof window.open }).originalOpen = window.open; window.open = () => null; });
      await pdf.getByRole("button", { name: t["medical.documents.print"], exact: true }).click();
      await expect(pdf.getByRole("alert")).toContainText(t["medical.documents.popupBlocked"]);
      await page.evaluate(() => { window.open = (window as unknown as { originalOpen: typeof window.open }).originalOpen; });
    }
    await page.evaluate(() => {
      const original = window.open.bind(window);
      window.open = (...args) => {
        const target = original(...args);
        if (target) target.print = () => { target.document.documentElement.dataset.printRequested = "true"; };
        return target;
      };
    });
    const printing = page.waitForEvent("popup");
    const printAction = pdf.getByRole("button", { name: language === "kk" ? t["common.retry"] : t["medical.documents.print"], exact: true });
    await printAction.focus();
    await printAction.press("Enter");
    const printPage = await printing;
    await expect(printPage.locator("html")).toHaveAttribute("data-print-requested", "true");
    await expect(printPage.locator("img")).toHaveCount(pageCount);
    for (let index = 0; index < pageCount; index++) {
      expect(await printPage.locator("img").nth(index).evaluate((element: HTMLImageElement) => element.complete && element.naturalWidth > 500)).toBe(true);
      await printPage.locator("img").nth(index).screenshot({ path: info.outputPath(`print-page-${language}-${index + 1}.png`) });
    }
    await printPage.screenshot({ path: info.outputPath(`head-print-${language}.png`) });
    const printedPath = info.outputPath(`printed-${language}.pdf`);
    await printPage.pdf({ path: printedPath, preferCSSPageSize: true, printBackground: true });
    const printedPages = Number(execFileSync(process.env.E2E_PYTHON!, ["-c", "import sys; from pypdf import PdfReader; print(len(PdfReader(sys.argv[1]).pages))", printedPath], { windowsHide: true, encoding: "utf8" }).trim());
    expect(printedPages).toBe(pageCount);
    await printPage.close();
    await expect(exportHistory.getByText(t["medical.documents.document_print_requested"], { exact: true })).toBeVisible();
    await expect(exportHistory.getByText(/Synthetic medical head/)).toHaveCount(2);
    await exportHistory.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`export-history-${language}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (language === "kk") {
      await exportHistory.getByRole("button", { name: t["medical.documents.exportHistory"], exact: true }).click();
      fixture("head-documents-revoke", branchId);
      try {
        await exportHistory.getByRole("button", { name: t["medical.documents.exportHistory"], exact: true }).click();
        await expect(documents).toHaveCount(0);
        await expect(dialog.getByText(t["medical.denied"], { exact: true })).toBeVisible();
      } finally { fixture("head-documents-restore", branchId); }
    }
  });
}

for (const [language, t] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  for (const width of [1440, 390]) test(`documents ${language} ${width}: drafts history recovery and clinical retention`, async ({ page, browser }, info) => {
    test.setTimeout(process.env.E2E_MEDICAL_FILES === "1" && language === "ru" && width === 1440 ? 210_000 : 150_000);
    const id = process.env.E2E_MEDICAL_FILES === "1"
      ? JSON.parse(execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-new-appointment"], {
        env: process.env, windowsHide: true, encoding: "utf8",
      }).trim().split(/\r?\n/).at(-1)!).appointment_id as number
      : (["ru", "kk", "en"] as const).indexOf(language) * 2 + (width === 1440 ? 1 : 2);
    const base = process.env.E2E_API_BASE_URL;
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await page.locator('form button[type="submit"]').click();
    const token = (await (await login).json()).access;
    await expect(page).toHaveURL(/\/app\//);
    const headContext = await browser.newContext();
    let headToken: string;
    try {
      const head = await headContext.newPage();
      await head.goto(`${process.env.E2E_BASE_URL}/login`);
      await head.locator('input[name="email"]').fill("medical-template-head@example.test");
      await head.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const authentication = head.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await head.locator('form button[type="submit"]').click();
      const response = await authentication;
      expect(response.ok()).toBe(true); headToken = (await response.json()).access;
    } finally { await headContext.close(); }
    const title = `Synthetic document ${language} ${width} patient-${id}${language === "en" && width === 390 ? " " + "Long".repeat(35) : ""}`;
    const command = async (path: string, data: object, auth = token) => {
      const response = await page.request.post(`${base}/api/medical/document-templates/${path}`, {
        headers: { Authorization: `Bearer ${auth}`, "Idempotency-Key": crypto.randomUUID() }, data });
      expect(response.ok(), await response.text()).toBe(true); return response.json();
    };
    const template = await command("", { business_id: 1, title,
      text: "Synthetic approved source {{record.number}} / {{doctor.full_name}} / {{patient.full_name}} / {{clinical.plan}} / {{unsupported}}\n{{clinical.plan_steps}}", reason: "" });
    await command(`versions/${template.version_id}/submit/`, { business_id: 1 });
    await command(`versions/${template.version_id}/decision/`, { business_id: 1, decision: "approved", reason: "Synthetic review" }, headToken);
    const response = await page.request.get(`${base}/api/appointments/${id}/`, { headers: { Authorization: `Bearer ${token}` } });
    expect(response.ok()).toBe(true);
    const appointment = await response.json();
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await openClinicalWorkspace(page);
    const workspace = page.getByTestId("clinical-workspace");
    await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`DOC-${id}`);
    await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
    await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
    await workspace.getByRole("button", { name: t["medical.plan.addStep"], exact: true }).click();
    await workspace.getByLabel(t["medical.plan.step"].replace("{number}", "1"), { exact: true }).fill("Synthetic plan {{patient.iin}} <b>literal</b>");
    await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true })).toBeDisabled();
    const complaint = workspace.getByLabel(t["medical.clinical.complaints"], { exact: true });
    await complaint.fill("Unsaved clinical content survives document save");
    await workspace.getByRole("tab", { name: t["medical.documents.title"], exact: true }).click();
    const documents = workspace.getByTestId("medical-documents");
    await expect(documents.getByText(t["medical.documents.empty"], { exact: true })).toBeVisible();
    await workspace.screenshot({ path: info.outputPath("documents-empty.png") });
    await documents.getByRole("button", { name: t["medical.documents.create"], exact: true }).click();
    const editor = page.getByTestId("medical-document-editor");
    await expect(editor.getByRole("button", { name: new RegExp(title) })).toBeVisible();
    const search = editor.getByRole("form", { name: t["medical.templates.search"], exact: true });
    await search.getByRole("textbox", { name: t["medical.templates.searchText"], exact: true }).fill("No synthetic match");
    await search.getByRole("button", { name: t["medical.templates.search"], exact: true }).click();
    await expect(editor.getByText(t["medical.templates.noMatches"], { exact: true })).toBeVisible();
    await editor.screenshot({ path: info.outputPath("document-search-empty.png") });
    await search.getByRole("textbox", { name: t["medical.templates.searchText"], exact: true }).fill(title);
    await search.getByRole("button", { name: t["medical.templates.search"], exact: true }).click();
    await expect(editor.getByRole("button", { name: new RegExp(title) })).toBeVisible();
    await editor.screenshot({ path: info.outputPath("document-template-picker.png") });
    await command(`${template.id}/availability/`, { business_id: 1, is_active: false,
      expected_revision: 0, reason: "Synthetic pause during selection" }, headToken);
    await editor.getByRole("button", { name: new RegExp(title) }).click();
    await expect(editor.getByRole("alert")).toBeVisible();
    const chooseAnother = editor.getByRole("button", { name: t["medical.documents.changeTemplate"], exact: true });
    await expect(chooseAnother).toBeVisible();
    await editor.screenshot({ path: info.outputPath("document-paused-template.png") });
    await command(`${template.id}/availability/`, { business_id: 1, is_active: true,
      expected_revision: 1, reason: "Synthetic resume before reselection" }, headToken);
    await chooseAnother.click();
    await expect(editor.getByRole("button", { name: new RegExp(title) })).toBeVisible();
    let failPreview = true;
    await page.route("**/api/medical/documents/preview/**", route => {
      if (failPreview) { failPreview = false; return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic preview unavailable"}' }); }
      return route.continue();
    });
    await editor.getByRole("button", { name: new RegExp(title) }).click();
    await expect(editor.getByRole("alert")).toBeVisible();
    await editor.screenshot({ path: info.outputPath("document-preview-retry.png") });
    await editor.getByRole("button", { name: t["common.retry"], exact: true }).click();
    const text = editor.getByRole("textbox", { name: t["medical.documents.text"], exact: true });
    await expect(text).toHaveValue(new RegExp(`Synthetic approved source DOC-${id} / Synthetic clinician / .+ /  / {{unsupported}}`));
    expect(await text.inputValue()).not.toContain("{{patient.full_name}}");
    await expect(text).toHaveValue(/\n1\. Synthetic plan \{\{patient.iin\}\} <b>literal<\/b>$/);
    await expect(editor.getByText(t["medical.documents.missingFields"].replace("{count}", "1"), { exact: true })).toBeVisible();
    await expect(editor.getByText(t["medical.documents.unknownFields"].replace("{count}", "1"), { exact: true })).toBeVisible();
    await editor.screenshot({ path: info.outputPath("document-preview-filled.png") });
    await text.fill(`Synthetic document original ${id}`);
    page.once("dialog", dialog => dialog.dismiss());
    await page.keyboard.press("Escape");
    await expect(text).toHaveValue(`Synthetic document original ${id}`);
    await editor.screenshot({ path: info.outputPath("document-editor.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="medical-document-editor"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    let fail = true;
    let releaseSave: (() => void) | undefined;
    const keys: string[] = [];
    await page.route("**/api/medical/documents/", async route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic temporary failure"}' }); }
      await new Promise<void>(resolve => { releaseSave = resolve; });
      await route.continue();
    });
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor.getByRole("alert")).toBeVisible();
    await expect(text).toHaveValue(`Synthetic document original ${id}`);
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect.poll(() => Boolean(releaseSave)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(editor).toBeVisible();
    releaseSave!();
    await expect(editor).not.toBeVisible();
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await documents.getByRole("button", { name: new RegExp(title) }).click();
    const detail = documents.getByTestId("medical-document-detail");
    await expect(detail.getByTestId("medical-document-text")).toHaveText(`Synthetic document original ${id}`);
    await expect(detail).toContainText("Synthetic clinician");
    const review = detail.getByTestId("document-review");
    await review.getByRole("button", { name: t["medical.documents.submitReview"], exact: true }).click();
    await review.getByRole("button", { name: t["medical.documents.returnDraft"], exact: true }).click();
    await expect(review.getByRole("textbox", { name: t["medical.documents.returnReason"], exact: true })).toBeVisible();
    await review.getByRole("button", { name: t["common.cancel"], exact: true }).click();
    await expect(review.getByRole("textbox")).toHaveCount(0);
    await review.getByRole("button", { name: t["medical.documents.confirmReview"], exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(detail.getByText(t["medical.documents.reviewed"], { exact: true })).toBeVisible();
    const returnReason = review.getByRole("textbox", { name: t["medical.documents.returnReason"], exact: true });
    await expect(returnReason).toBeVisible();
    await expect(detail.getByRole("button", { name: t["medical.documents.edit"], exact: true })).toHaveCount(0);
    await returnReason.fill(`Synthetic review return ${id}`);
    page.once("dialog", dialog => dialog.dismiss());
    await documents.getByRole("button", { name: t["medical.documents.back"], exact: true }).click();
    await expect(returnReason).toHaveValue(`Synthetic review return ${id}`);
    let failReview = true;
    const reviewKeys: string[] = [];
    await page.route("**/review-transition/", route => {
      reviewKeys.push(route.request().headers()["idempotency-key"]);
      if (failReview) { failReview = false; return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic review unavailable"}' }); }
      return route.continue();
    });
    await review.getByRole("button", { name: t["medical.documents.returnDraft"], exact: true }).click();
    await expect(review.getByRole("alert")).toBeVisible();
    await expect(returnReason).toHaveValue(`Synthetic review return ${id}`);
    await review.getByRole("button", { name: t["medical.documents.returnDraft"], exact: true }).click();
    await expect(review.getByRole("button", { name: t["medical.documents.submitReview"], exact: true })).toBeVisible();
    expect(reviewKeys).toHaveLength(2); expect(reviewKeys[0]).toBe(reviewKeys[1]);
    await page.unroute("**/review-transition/");
    await review.getByRole("button", { name: t["medical.documents.reviewHistory"], exact: true }).click();
    await expect(review).toContainText(`Synthetic review return ${id}`);
    await expect(review).toContainText(t["medical.documents.reviewSubmitted"]);
    await expect(review).toContainText(t["medical.documents.reviewConfirmed"]);
    await expect(detail.getByText(t["medical.documents.reviewed"], { exact: true })).toHaveCount(0);
    await review.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath("document-review-history.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (process.env.E2E_MEDICAL_FILES === "1") {
      const pdf = detail.getByTestId("medical-document-pdf");
      let failPrepare = true;
      await page.route("**/api/medical/documents/versions/*/pdf-prepare/", route => {
        if (failPrepare) {
          failPrepare = false;
          return route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Synthetic artifact unavailable"}' });
        }
        return route.continue();
      });
      await pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true }).click();
      await expect(pdf.getByRole("alert")).toBeVisible();
      await pdf.getByRole("button", { name: t["common.retry"], exact: true }).click();
      await expect(pdf.getByRole("status")).toContainText(t["medical.files.pending"]);
      await expect(pdf.getByTestId("medical-pdf-preview")).toHaveCount(0);
      execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "document-artifacts-scan", String(id)], {
        env: process.env, windowsHide: true, stdio: "pipe",
      });
      await pdf.getByRole("button", { name: t["common.retry"], exact: true }).click();
      await expect(pdf.getByTestId("medical-pdf-text")).toContainText(`Synthetic document original ${id}`);
      await expect(pdf.locator("canvas")).toBeVisible();
      await pdf.scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("document-pdf-inline.png") });
      if (width === 390) {
        await pdf.getByLabel(t["medical.files.pdfZoom"], { exact: true }).click();
        await page.getByRole("option", { name: "300%", exact: true }).click();
        await expect(pdf.getByTestId("medical-pdf-text")).toContainText(`Synthetic document original ${id}`);
        await pdf.scrollIntoViewIfNeeded();
        await page.screenshot({ path: info.outputPath("document-pdf-mobile-zoom.png") });
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await pdf.getByRole("button", { name: t["common.close"], exact: true }).click();
      await expect(pdf.getByTestId("medical-pdf-preview")).toHaveCount(0);
      await expect(pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true })).toBeFocused();
      await page.unroute("**/api/medical/documents/versions/*/pdf-prepare/");
    }
    await detail.getByRole("button", { name: t["medical.documents.edit"], exact: true }).click();
    await expect(text).toHaveValue(`Synthetic document original ${id}`);
    await text.fill(`Synthetic document corrected ${id}`);
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor).not.toBeVisible();
    await documents.getByRole("button", { name: new RegExp(title) }).click();
    await expect(detail.getByTestId("medical-document-text")).toHaveText(`Synthetic document corrected ${id}`);
    await workspace.screenshot({ path: info.outputPath("document-current.png") });
    await detail.getByRole("button", { name: t["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
    await expect(detail.getByTestId("medical-document-text")).toHaveText(`Synthetic document original ${id}`);
    await expect(detail.getByText(t["medical.documents.recorded"], { exact: true })).toBeVisible();
    await expect(detail.getByRole("button", { name: t["medical.documents.edit"], exact: true })).toHaveCount(0);
    await workspace.screenshot({ path: info.outputPath("document-history.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-workspace"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await documents.getByRole("button", { name: t["medical.documents.back"], exact: true }).click();
    await expect(documents.getByRole("button", { name: new RegExp(title) })).toBeFocused();
    await documents.getByRole("button", { name: new RegExp(title) }).click();
    await detail.getByRole("button", { name: t["medical.documents.edit"], exact: true }).click();
    await text.fill("Synthetic stale draft retained");
    await page.route("**/api/medical/documents/*/draft/", route => route.fulfill({ status: 409, contentType: "application/json", body: '{"detail":"Synthetic stale revision"}' }));
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor).toContainText(t["medical.clinical.conflict"]);
    await expect(text).toHaveValue("Synthetic stale draft retained");
    await expect(editor.getByRole("button", { name: t["medical.clinical.save"], exact: true })).toBeDisabled();
    await editor.screenshot({ path: info.outputPath("document-conflict.png") });
    page.once("dialog", dialog => dialog.accept());
    await editor.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(editor).not.toBeVisible();
    await page.unroute("**/api/medical/documents/*/draft/");
    await documents.getByRole("button", { name: new RegExp(title) }).click();
    await expect(detail.getByTestId("medical-document-text")).toHaveText(`Synthetic document corrected ${id}`);
    await detail.getByRole("button", { name: t["medical.documents.edit"], exact: true }).click();
    await text.fill("Synthetic revoked draft");
    await page.route("**/api/medical/documents/*/draft/", route => route.fulfill({ status: 403, contentType: "application/json", body: '{"detail":"Synthetic document access revoked"}' }));
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor).not.toBeVisible();
    await expect(documents).toContainText(t["medical.denied"]);
    await expect(detail).toHaveCount(0);
    await expect(documents.getByRole("button", { name: t["medical.documents.create"], exact: true })).toHaveCount(0);
    await page.unroute("**/api/medical/documents/*/draft/");
    await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
    const clinicalHistory = workspace.getByTestId("clinical-history");
    await clinicalHistory.locator("ul > li > button").first().click();
    await clinicalHistory.getByRole("button", { name: t["medical.documents.title"], exact: true }).click();
    const historical = page.getByTestId("historical-documents");
    await historical.getByRole("button", { name: new RegExp(title) }).click();
    await expect(historical.getByTestId("medical-document-text")).toHaveText(`Synthetic document corrected ${id}`);
    await expect(historical.getByRole("button", { name: t["medical.documents.edit"], exact: true })).toHaveCount(0);
    await expect(historical.getByRole("button", { name: t["medical.documents.create"], exact: true })).toHaveCount(0);
    await historical.screenshot({ path: info.outputPath("calendar-historical-document.png") });
    await page.keyboard.press("Escape");
    await expect(historical).not.toBeVisible();
    await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
    await expect(complaint).toHaveValue("Unsaved clinical content survives document save");
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("clinical-unsaved")).toBeVisible();
    expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic document original");
    if (process.env.E2E_MEDICAL_FILES === "1" && language === "ru" && width === 1440) {
      const fixture = JSON.parse(execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "document-correction-prepare", String(id)], {
        env: process.env, windowsHide: true, encoding: "utf8",
      }).trim().split(/\r?\n/).at(-1)!);
      page.once("dialog", dialog => dialog.accept());
      await page.goto(`/app/clients/${fixture.client_id}`);
      await page.getByTestId("patient-administration").getByLabel(t["medical.branch"], { exact: true }).click();
      await page.getByRole("option", { name: "First", exact: true }).click();
      await page.getByTestId(`correction-access-${fixture.correction_id}`).getByRole("button", { name: t["medical.correctionAccess.edit"], exact: true }).click();
      const correction = page.getByRole("dialog");
      const pdf = correction.getByTestId("medical-document-pdf");
      await pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true }).click();
      await expect(pdf.getByRole("status")).toContainText(t["medical.files.pending"]);
      execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "document-artifacts-scan", String(id)], {
        env: process.env, windowsHide: true, stdio: "pipe",
      });
      await pdf.getByRole("button", { name: t["common.retry"], exact: true }).click();
      await expect(pdf.getByTestId("medical-pdf-text")).toContainText(`Synthetic document corrected ${id}`);
      await pdf.scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("correction-pdf-desktop.png") });
      await page.setViewportSize({ width: 390, height: 900 });
      await pdf.scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("correction-pdf-mobile.png") });
      const correctedText = correction.getByRole("textbox", { name: t["medical.correctionAccess.document"], exact: true });
      await correctedText.fill("Synthetic unsaved correction");
      await expect(pdf).toHaveCount(0);
      await expect(correctedText).toHaveValue("Synthetic unsaved correction");
      await correctedText.fill(`Synthetic document corrected ${id}`);
      execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "document-correction-expire", String(fixture.correction_id)], {
        env: process.env, windowsHide: true, stdio: "pipe",
      });
      try {
        await pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true }).click();
        await expect(correction).toHaveCount(0);
        await expect(page.getByTestId("patient-administration").getByRole("alert")).toBeVisible();
      } finally {
        execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "document-correction-clock-reset"], {
          env: process.env, windowsHide: true, stdio: "pipe",
        });
      }
    }
  });
}
