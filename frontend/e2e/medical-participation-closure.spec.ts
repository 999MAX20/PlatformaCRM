import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
for (const mode of ["ru", "kk", "denied"] as const) test(`own participation closure ${mode}: resolve obligations and revoke access`, async ({ page }, info) => {
  const t = mode === "kk" ? kk : ru;
  const fixture = (command: string, ...args: string[]) => execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", command, ...args],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(fixture("participation-closure-prepare").trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), mode === "kk" ? "kk" : "ru");
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(entry.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/calendar");
  await page.locator("summary").filter({ hasText: t["medical.participation.title"] }).click();
  await page.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
  const row = page.getByTestId(`participation-row-${entry.participation_id}`);
  await row.getByRole("button", { name: t["medical.participation.endOwn"], exact: true }).click();
  const panel = page.getByTestId("participation-closure");
  await expect(panel).toContainText(t["medical.participation.remaining"]);
  await expect(panel.getByRole("link", { name: t["medical.participation.appointmentRef"].replace("{id}", String(entry.appointment_id)), exact: true })).toBeVisible();
  const confirm = panel.getByRole("button", { name: t["medical.participation.endOwnConfirm"], exact: true });
  await expect(confirm).toHaveCount(0);
  await panel.screenshot({ path: info.outputPath("closure-obligations-desktop.png") });
  fixture("participation-closure-resolve", String(entry.participation_id));
  await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(confirm).toBeEnabled();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: info.outputPath("closure-ready-mobile.png") });
  await page.route("**/end-own/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  await confirm.focus(); await page.keyboard.press("Enter");
  await expect(panel.getByRole("alert")).toBeVisible();
  await page.unroute("**/end-own/");
  if (mode === "denied") {
    await page.route("**/end-own/", route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked" } }));
    await confirm.click();
    await expect(panel).toHaveCount(0);
    await expect(page.getByRole("dialog", { name: t["medical.participation.title"], exact: true })).toContainText(t["medical.denied"]);
    return;
  }
  if (mode === "kk") {
    await page.route("**/end-own/", route => route.fulfill({ status: 409, json: { detail: "Synthetic stale participation" } }));
    await confirm.click();
    await expect(confirm).toBeDisabled();
    await page.unroute("**/end-own/");
    await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).first().click();
    await expect(confirm).toBeEnabled();
  }
  await confirm.click();
  await expect(panel).toHaveCount(0);
  await expect(row).toContainText(t["medical.participation.state.ended"]);
  await expect(row.getByRole("button", { name: t["medical.clinical.history"], exact: true })).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("closure-ended-mobile.png") });
});

test("head sees obligations and assigns remaining responsibility without reassigning appointments", async ({ page }, info) => {
  const t = ru;
  const raw = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "participation-closure-prepare-head"],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const entry = JSON.parse(raw.trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(entry.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients/${entry.client_id}`);
  await page.getByTestId("patient-administration").getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
  const row = page.getByTestId(`participation-row-${entry.participation_id}`);
  await row.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
  await expect(page.getByTestId("participation-closure")).toContainText(t["medical.participation.remaining"]);
  const form = page.getByTestId("participation-command-form");
  await form.getByRole("combobox", { name: t["medical.participation.responsible"] }).click();
  await page.getByRole("option", { name: "Synthetic Lead", exact: true }).click();
  await form.getByRole("textbox", { name: t["medical.participation.reason"], exact: true }).fill(`Synthetic reassignment responsibility ${entry.participation_id}`);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("dialog", { name: t["medical.participation.title"], exact: true }).screenshot({ path: info.outputPath("head-closure-mobile.png") });
  await form.getByRole("button", { name: t["medical.participation.end"], exact: true }).click();
  await expect(row).toContainText(t["medical.participation.state.ended"]);
});
