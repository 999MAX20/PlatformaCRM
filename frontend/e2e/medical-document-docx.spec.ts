import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { ru as t } from "../src/lib/i18n/ru";
import { openClinicalWorkspace } from "./clinical-card-navigation";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test("DOCX permitted draft: quarantine retry exact download and review denial", async ({ page, browser }, info) => {
  test.setTimeout(120_000);
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("files-new-appointment").trim().split(/\r?\n/).at(-1)!);
  const title = `Synthetic DOCX ${crypto.randomUUID()}`;
  let headToken = "";
  let kindId = 0;
  let templateId = 0;
  async function login(target: Page, email: string) {
    await target.goto(`${process.env.E2E_BASE_URL}/login`);
    await target.locator('input[name="email"]').fill(email);
    await target.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const auth = target.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await target.locator('form button[type="submit"]').click();
    const response = await auth; expect(response.ok()).toBe(true);
    await expect(target).toHaveURL(/\/app\//);
    return (await response.json()).access as string;
  }
  const headContext = await browser.newContext();
  try {
    const head = await headContext.newPage();
    const token = await login(head, "medical-template-head@example.test");
    headToken = token;
    const command = async (path: string, data: object) => {
      const response = await head.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/${path}`, {
        headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() }, data });
      expect(response.ok(), await response.text()).toBe(true); return response.json();
    };
    const template = await command("document-templates/common/", { business_id: 1, title, text: "Synthetic draft text", reason: "" });
    await command(`document-templates/common/versions/${template.version_id}/submit/`, { business_id: 1 });
    await command(`document-templates/versions/${template.version_id}/decision/`, { business_id: 1, decision: "approved", reason: "" });
    templateId = template.id;
    const kind = await command("document-kinds/", { business_id: 1, template_ids: [template.id], reason: "Synthetic DOCX permission",
      content: { name: title, docx_allowed: true, services: [], default: { required_at: "before_completion", required_fields: ["patient.full_name", "clinic.license"],
        reviewers: ["primary_clinician"], signers: [], issuable: false } } });
    kindId = kind.kind_id;
  } finally { await headContext.close(); }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  const token = await login(page, "medical-role-doctor@example.test");
  const appointment = await (await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${entry.appointment_id}/`,
    { headers: { Authorization: `Bearer ${token}` } })).json();
  await page.goto(`/app/calendar?appointment=${entry.appointment_id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`DOCX-${entry.appointment_id}`);
  await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await workspace.getByRole("tab", { name: t["medical.documents.title"], exact: true }).click();
  const documents = workspace.getByTestId("medical-documents");
  await documents.getByRole("button", { name: t["medical.documents.create"], exact: true }).click();
  const editor = page.getByTestId("medical-document-editor");
  await editor.getByRole("button", { name: new RegExp(title) }).click();
  await editor.getByRole("textbox", { name: t["medical.documents.text"], exact: true }).fill(`Synthetic exported content ${entry.appointment_id}`);
  await expect(editor.getByRole("button", { name: t["medical.templates.downloadDocx"], exact: true })).toBeEnabled();
  const templateDownloaded = page.waitForEvent("download");
  await editor.getByRole("button", { name: t["medical.templates.downloadDocx"], exact: true }).click();
  await templateDownloaded;
  await expect(editor).toBeVisible();
  await editor.getByTestId("template-docx").screenshot({ path: info.outputPath("doctor-template-action-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await editor.getByTestId("template-docx").screenshot({ path: info.outputPath("doctor-template-action-mobile.png") });
  await expect(editor.getByRole("textbox", { name: t["medical.documents.text"], exact: true })).toHaveValue(`Synthetic exported content ${entry.appointment_id}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
  await expect(editor).not.toBeVisible();
  await documents.getByRole("button", { name: new RegExp(title) }).click();
  const detail = documents.getByTestId("medical-document-detail");
  const changedRules = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/document-kinds/${kindId}/save/`, {
    headers: { Authorization: `Bearer ${headToken}`, "Idempotency-Key": crypto.randomUUID() }, data: {
      business_id: 1, expected_revision: 1, template_ids: [templateId], reason: "Synthetic future policy",
      content: { name: "Synthetic changed rules", docx_allowed: false, services: [], default: {
        required_at: "optional", required_fields: [], reviewers: ["primary_clinician"], signers: [], issuable: false,
      } },
    },
  });
  expect(changedRules.ok(), await changedRules.text()).toBe(true);
  const savedRules = detail.getByTestId("document-saved-rules");
  await page.route("**/requirements/**", route => route.fulfill({ status: 503, json: { detail: "Synthetic requirements outage" } }));
  await savedRules.locator("summary").click();
  const presence = savedRules.getByTestId("document-field-presence");
  await expect(presence.getByRole("button", { name: t["common.retry"], exact: true })).toBeVisible();
  await expect(detail.getByTestId("medical-document-text")).toContainText(`Synthetic exported content ${entry.appointment_id}`);
  await page.unroute("**/requirements/**");
  await presence.getByRole("button", { name: t["common.retry"], exact: true }).click();
  await expect(presence.getByRole("listitem").filter({ hasText: t["medical.fullName"] })).toContainText(t["medical.rules.fieldPresent"]);
  await expect(presence.getByRole("listitem").filter({ hasText: t["medical.credentials.license"] })).toContainText(t["medical.rules.fieldMissing"]);
  await expect(savedRules).toContainText(title);
  await expect(savedRules).toContainText(t["medical.rules.moment.before_completion"]);
  await expect(savedRules).toContainText(t["medical.fullName"]);
  await expect(savedRules).not.toContainText("Synthetic changed rules");
  await savedRules.screenshot({ path: info.outputPath("saved-rules-desktop.png") });
  await presence.screenshot({ path: info.outputPath("required-fields-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await savedRules.screenshot({ path: info.outputPath("saved-rules-mobile.png") });
  await presence.evaluate(element => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("required-fields-mobile.png") });
  await savedRules.locator("summary").click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  const pdf = detail.getByTestId("medical-document-pdf");
  const preparing = page.waitForResponse(r => r.url().endsWith("/pdf-prepare/") && r.request().method() === "POST");
  await pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true }).click();
  const preparedResponse = await preparing;
  const artifact = await preparedResponse.json();
  const scope = preparedResponse.request().postDataJSON();
  await pdf.getByRole("button", { name: t["medical.documents.downloadDocx"], exact: true }).click();
  await expect(pdf.getByRole("status").filter({ hasText: "DOCX:" })).toContainText(t["medical.files.pending"]);
  await pdf.screenshot({ path: info.outputPath("docx-pending-desktop.png") });
  fixture("document-artifacts-scan", String(entry.appointment_id));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/docx-download/", route => route.fulfill({ status: 503, json: { detail: "Synthetic DOCX failure" } }), { times: 1 });
  await pdf.getByRole("button", { name: t["medical.documents.downloadDocx"], exact: true }).click();
  await expect(pdf.getByRole("alert")).toBeVisible();
  await pdf.screenshot({ path: info.outputPath("docx-retry-mobile.png") });
  const downloading = page.waitForEvent("download");
  await pdf.getByRole("alert").getByRole("button", { name: t["common.retry"], exact: true }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toMatch(/\.docx$/);
  const path = info.outputPath("synthetic-download.docx"); await download.saveAs(path);
  const content = execFileSync(process.env.E2E_PYTHON!, ["-c", "import sys; from docx import Document; d=Document(sys.argv[1]); print(' '.join(p.text for p in d.paragraphs)); print(' '.join(p.text for p in d.sections[0].header.paragraphs))", path],
    { env: { ...process.env, PYTHONIOENCODING: "utf-8" }, windowsHide: true, encoding: "utf8" });
  expect(content).toContain(`Synthetic exported content ${entry.appointment_id}`); expect(content).toContain("Черновик");
  const reviewed = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/documents/versions/${artifact.version_id}/review-transition/`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() }, data: {
      business_id: scope.business_id, patient_id: scope.patient_id, appointment_id: entry.appointment_id,
      expected_state_revision: 1, target: "ready_for_review", reason: "",
    },
  });
  expect(reviewed.ok(), await reviewed.text()).toBe(true);
  await pdf.getByRole("button", { name: t["medical.documents.downloadDocx"], exact: true }).click();
  const conflict = pdf.getByRole("status").filter({ has: page.getByRole("button", { name: t["common.retry"], exact: true }) });
  await expect(conflict).toBeVisible();
  await expect(pdf.getByRole("button", { name: t["medical.documents.downloadDocx"], exact: true })).toHaveCount(0);
  await pdf.screenshot({ path: info.outputPath("docx-conflict-mobile.png") });
  const refreshed = page.waitForResponse(r => r.url().endsWith("/pdf-prepare/") && r.request().method() === "POST");
  await conflict.getByRole("button", { name: t["common.retry"], exact: true }).click();
  const refreshedResponse = await refreshed;
  expect(refreshedResponse.ok()).toBe(true);
  expect((await refreshedResponse.json()).can_docx).toBe(false);
  await expect(pdf.getByRole("button", { name: t["medical.documents.pdfPreview"], exact: true })).toBeEnabled();
  await expect(conflict).toHaveCount(0);
  await expect(pdf.getByRole("button", { name: t["medical.documents.downloadDocx"], exact: true })).toHaveCount(0);
  await page.route("**/requirements/**", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked access" } }));
  await savedRules.locator("summary").click();
  await expect(detail).toHaveCount(0);
  await expect(documents.getByText(title, { exact: true })).toHaveCount(0);
});
