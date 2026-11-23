import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { kk } from "../src/lib/i18n/kk";
import { ru } from "../src/lib/i18n/ru";
import { taskDateInput } from "../src/features/tasks/workspaceUtils";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
for (const mode of ["ru", "kk", "denied"] as const) test(`doctor records actual visit ${mode}: desktop mobile retained input and clinical entry`, async ({ page }, info) => {
  const t = mode === "kk" ? kk : ru;
  const fixture = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "actual-visit-prepare"],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture.trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), mode === "kk" ? "kk" : "ru");
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(entry.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients?client=${entry.client_id}${mode === "kk" ? "" : "&tab=timeline"}`);
  const client = mode === "kk" ? page.getByTestId("patient-administration") : page.getByRole("dialog", { name: t["common.client"], exact: true });
  if (mode !== "kk") await client.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
  await client.getByRole("button", { name: t["medical.actual.title"], exact: true }).click();
  const dialog = page.getByTestId("medical-actual-visit");
  await dialog.getByLabel(t["appointment.service"], { exact: true }).click();
  await page.getByRole("option", { name: "Synthetic consultation", exact: true }).click();
  await dialog.getByLabel(t["appointment.resource"], { exact: true }).click();
  await page.getByRole("option", { name: "Synthetic clinician", exact: true }).click();
  await dialog.getByLabel(t["medical.actual.start"], { exact: true }).fill(taskDateInput(entry.actual_start, entry.timezone));
  await dialog.getByRole("textbox", { name: t["medical.actual.reason"], exact: true }).fill(`Synthetic actual visit ${entry.client_id}`);
  await dialog.screenshot({ path: info.outputPath("actual-visit-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath("actual-visit-mobile.png") });
  const submit = dialog.getByRole("button", { name: t["medical.actual.confirm"], exact: true });
  await page.route("**/actual-visit/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  await submit.focus(); await page.keyboard.press("Enter");
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: t["medical.actual.reason"], exact: true })).toHaveValue(`Synthetic actual visit ${entry.client_id}`);
  await page.unroute("**/actual-visit/");
  if (mode === "denied") {
    await page.route("**/actual-visit/", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked access" } }));
    await submit.click();
    await expect(dialog).toContainText(t["medical.denied"]);
    await expect(dialog.getByRole("textbox")).toHaveCount(0);
    return;
  }
  if (mode === "kk") {
    await page.route("**/actual-visit/", route => route.fulfill({ status: 409, json: { detail: "Synthetic changed booking" } }));
    await submit.click();
    await expect(submit).toBeDisabled();
    await page.unroute("**/actual-visit/");
    await dialog.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(submit).toBeEnabled();
  }
  await submit.click();
  await expect(dialog.getByRole("status")).toContainText(t["medical.actual.saved"]);
  await dialog.getByRole("button", { name: t["medical.plan.openBooking"], exact: true }).click();
  await expect(page).toHaveURL(/\/app\/calendar\?appointment=/);
  await expect(page.getByTestId("clinical-workspace")).toBeVisible();
  const clinical = page.getByTestId("clinical-workspace");
  await clinical.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
  await clinical.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await expect(clinical.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("actual-visit-calendar-mobile.png") });
});
