import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { kk } from "../src/lib/i18n/kk";
import { ru as t } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { openClinicalWorkspace } from "./clinical-card-navigation";

requireIsolatedEnvironment();
for (const language of ["ru", "kk"] as const) test(`head signs ${language} exact synthetic PDF: desktop, mobile and retry`, async ({ page }, info) => {
  const text = language === "kk" ? kk : t;
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("files-new-appointment").trim().split(/\r?\n/).at(-1)!);
  fixture("historical-orders-context", String(entry.appointment_id));
  const document = JSON.parse(fixture("signing-prepare", String(entry.appointment_id)).trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-participation-head@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients?client=${entry.client_id}&tab=timeline`);
  const dialog = page.getByRole("dialog", { name: text["common.client"], exact: true });
  await dialog.getByRole("tab", { name: text["medical.clinical.title"], exact: true }).click();
  await dialog.getByLabel(text["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  await dialog.getByTestId("medical-documents").getByRole("button", { name: new RegExp(document.title) }).click();
  const signing = dialog.getByTestId("document-signing");
  const sign = signing.getByRole("button", { name: text["medical.signing.sign"], exact: true });
  await expect(sign).toBeEnabled();
  await expect(dialog.getByTestId("document-head-review")).toHaveCount(1);
  await expect(dialog.getByTestId("document-head-review").getByText(text["medical.documents.headConfirmed"], { exact: true })).toBeVisible();
  const preview = signing.getByTestId("signing-pdf");
  await preview.getByRole("button", { name: text["medical.signing.preview"], exact: true }).click();
  await expect(preview.locator("canvas")).toBeVisible();
  await preview.screenshot({ path: info.outputPath("signing-exact-pdf.png") });
  await preview.getByRole("button", { name: text["common.close"], exact: true }).click();
  await expect(preview.getByRole("button", { name: text["medical.signing.preview"], exact: true })).toBeFocused();
  await signing.screenshot({ path: info.outputPath("signing-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await signing.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("signing-mobile.png") });
  if (language === "kk") {
    await page.route("**/advance-signing/", route => route.fulfill({ status: 409, json: { detail: "Synthetic changed session" } }));
    await sign.click();
    await expect(sign).toBeDisabled();
    await page.unroute("**/advance-signing/");
    page.once("dialog", dialog => dialog.accept());
    await signing.getByRole("button", { name: text["medical.clinical.reload"], exact: true }).click();
    await expect(sign).toBeEnabled();
  }
  await page.route("**/advance-signing/", route => route.fulfill({ status: 503, json: { detail: "Synthetic signature outage" } }));
  await sign.focus(); await page.keyboard.press("Enter");
  await expect(signing.getByRole("alert")).toBeVisible();
  await page.unroute("**/advance-signing/");
  await sign.click();
  await expect(signing.getByRole("status")).toHaveText(text["medical.signing.completed"]);
  await expect(sign).toHaveCount(0);
  await expect(dialog.getByTestId("document-head-review")).toHaveCount(1);
  await expect(dialog.getByTestId("document-head-review").getByText(text["medical.documents.headConfirmed"], { exact: true })).toBeVisible();
  await signing.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("signing-completed-mobile.png") });
  if (language === "kk") {
    await page.route("**/signing/?*", route => route.fulfill({ status: 403, json: { detail: "Synthetic access revoked" } }));
    await signing.getByRole("button", { name: text["medical.signing.refresh"], exact: true }).click();
    await expect(dialog.getByTestId("medical-documents")).toHaveCount(0);
    await expect(dialog.getByRole("status")).toContainText(text["medical.denied"]);
  }
});

test("doctor prepares PDF, waits for scan, starts and cancels signing", async ({ page }, info) => {
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!,
    ["e2e/clinical-runtime.py", command, ...args], { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("files-new-appointment").trim().split(/\r?\n/).at(-1)!);
  fixture("historical-orders-context", String(entry.appointment_id));
  const document = JSON.parse(fixture("signing-doctor-prepare", String(entry.appointment_id)).trim().split(/\r?\n/).at(-1)!);
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
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
  await workspace.getByRole("tab", { name: t["medical.documents.title"], exact: true }).click();
  await workspace.getByTestId("medical-documents").getByRole("button", { name: new RegExp(document.title) }).click();
  const signing = page.getByTestId("document-signing");
  await signing.getByRole("button", { name: t["medical.signing.prepare"], exact: true }).click();
  await expect(signing).toContainText(t["medical.signing.quarantine"]);
  fixture("document-artifacts-scan", String(entry.appointment_id));
  await signing.getByRole("button", { name: t["medical.signing.refresh"], exact: true }).click();
  await signing.getByRole("button", { name: t["medical.signing.start"], exact: true }).click();
  await expect(signing.getByRole("button", { name: t["medical.signing.sign"], exact: true })).toBeEnabled();
  await page.setViewportSize({ width: 390, height: 844 });
  await signing.evaluate(node => node.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("doctor-signing-mobile.png") });
  await signing.getByRole("button", { name: t["medical.signing.cancel"], exact: true }).click();
  await expect(signing.getByRole("status")).toHaveText(t["medical.signing.cancelled"]);
  await expect(signing.getByRole("button", { name: t["medical.signing.sign"], exact: true })).toHaveCount(0);
});
