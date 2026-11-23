import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { openClinicalWorkspace } from "./clinical-card-navigation";

requireIsolatedEnvironment();
test("timed correction after completed encounter: edit and review in the exact grant", async ({ page }, info) => {
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("final-correction-prepare", "timed").trim().split(/\r?\n/).at(-1)!);
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(entry.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients/${entry.client_id}`);
  await page.getByTestId("patient-administration").getByLabel(ru["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "Synthetic completion branch", exact: true }).click();
  const row = page.getByTestId(`correction-access-${entry.grant_id}`);
  await row.getByRole("button", { name: ru["medical.correctionAccess.edit"], exact: true }).click();
  const dialog = page.getByRole("dialog", { name: ru["medical.correctionAccess.title"], exact: true });
  await dialog.getByRole("textbox", { name: ru["medical.correctionAccess.document"], exact: true }).fill("Timed correction after completed care");
  await dialog.getByRole("textbox", { name: ru["medical.reason"], exact: true }).fill("Synthetic transcription correction");
  await dialog.getByRole("button", { name: ru["medical.clinical.save"], exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await row.getByRole("button", { name: ru["medical.correctionAccess.edit"], exact: true }).click();
  await dialog.getByRole("button", { name: ru["medical.documents.submitReview"], exact: true }).click();
  await dialog.getByRole("button", { name: ru["medical.documents.confirmReview"], exact: true }).click();
  const signing = dialog.getByTestId("document-signing");
  await signing.getByRole("button", { name: ru["medical.signing.prepare"], exact: true }).click();
  await expect(signing).toContainText(ru["medical.signing.quarantine"]);
  fixture("document-artifacts-scan", String(entry.appointment_id));
  await signing.getByRole("button", { name: ru["medical.signing.refresh"], exact: true }).click();
  await signing.getByRole("button", { name: ru["medical.signing.finalize"], exact: true }).click();
  await expect(signing.getByTestId("document-finalization")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await signing.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("timed-correction-finalized-mobile.png") });
});

for (const language of ["ru", "kk"] as const) test(`correct finalized document ${language}: preserved source and fresh review`, async ({ page }, info) => {
  const text = language === "kk" ? kk : ru;
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("final-correction-prepare").trim().split(/\r?\n/).at(-1)!);
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.setViewportSize({ width: 1440, height: 1000 });
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
  await workspace.getByRole("tab", { name: text["medical.documents.title"], exact: true }).click();
  await workspace.getByTestId("medical-documents").getByRole("button", { name: new RegExp(entry.title) }).click();
  const correction = page.getByTestId("document-correction");
  await correction.getByRole("button", { name: text["medical.documents.correct"], exact: true }).click();
  await correction.getByRole("textbox", { name: text["medical.correctionAccess.document"], exact: true }).fill("Synthetic corrected content");
  await correction.getByRole("textbox", { name: text["medical.reason"], exact: true }).fill("Synthetic correction reason");
  await correction.screenshot({ path: info.outputPath("correction-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await correction.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("correction-mobile.png") });
  const save = correction.getByRole("button", { name: text["medical.clinical.save"], exact: true });
  if (language === "kk") {
    await page.route("**/versions/*/correction/", route => route.fulfill({ status: 409, json: { detail: "Synthetic conflict" } }));
    await save.click();
    await expect(save).toBeDisabled();
    await page.unroute("**/versions/*/correction/");
    page.once("dialog", dialog => dialog.accept());
    await correction.getByRole("button", { name: text["medical.clinical.reload"], exact: true }).click();
    await correction.getByRole("button", { name: text["medical.documents.correct"], exact: true }).click();
    await correction.getByRole("textbox", { name: text["medical.correctionAccess.document"], exact: true }).fill("Synthetic corrected content");
    await correction.getByRole("textbox", { name: text["medical.reason"], exact: true }).fill("Synthetic correction reason");
  }
  await page.route("**/versions/*/correction/", route => route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } }));
  await save.click();
  await expect(correction.getByRole("alert")).toBeVisible();
  await expect(correction.getByRole("textbox", { name: text["medical.reason"], exact: true })).toHaveValue("Synthetic correction reason");
  await page.unroute("**/versions/*/correction/");
  await save.click();
  await expect(page.getByTestId("medical-document-text")).toHaveText("Synthetic corrected content");
  await expect(page.getByTestId("document-review")).toContainText(text["medical.documents.correctiveVersion"]);
  await page.getByRole("button", { name: text["medical.documents.submitReview"], exact: true }).click();
  await page.getByRole("button", { name: text["medical.documents.confirmReview"], exact: true }).click();
  const signing = page.getByTestId("document-signing");
  await signing.getByRole("button", { name: text["medical.signing.prepare"], exact: true }).click();
  await expect(signing).toContainText(text["medical.signing.quarantine"]);
  // Scan only artifacts belonging to this newly created appointment.
  fixture("document-artifacts-scan", String(entry.appointment_id));
  await signing.getByRole("button", { name: text["medical.signing.refresh"], exact: true }).click();
  await signing.getByRole("button", { name: text["medical.signing.finalize"], exact: true }).click();
  await expect(signing.getByTestId("document-finalization")).toBeVisible();
  await page.getByTestId("medical-document-detail").getByRole("button", { name: text["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
  await expect(page.getByTestId("medical-document-text")).toHaveText("Synthetic original document");
  await expect(page.getByTestId("document-finalization")).toBeVisible();
  await expect(page.getByTestId("document-correction")).toHaveCount(0);
  await page.getByTestId("document-finalization").evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("original-finalized-mobile.png") });
  if (language === "kk") {
    await page.route("**/signing/?*", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked access" } }));
    await signing.getByRole("button", { name: text["medical.signing.refresh"], exact: true }).click();
    await expect(page.getByTestId("medical-document-text")).toHaveCount(0);
    await expect(page.getByTestId("medical-documents")).toContainText(text["medical.denied"]);
  }
});
