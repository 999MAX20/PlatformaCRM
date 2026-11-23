import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
let nextId = 7;
for (const language of ["ru", "kk", "en"] as const) for (const width of [1440, 390]) {
  const id = ++nextId;
  test(`client clinical entry ${language} ${width}: choose booking and save encounter`, async ({ page }, info) => {
    const t = { ru, kk, en }[language];
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
    await page.locator('form button[type="submit"]').click();
    const token = (await (await login).json()).access;
    await me;
    await expect(page).toHaveURL(/\/app\//);
    const headers = { Authorization: `Bearer ${token}` };
    const appointmentResponse = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${id}/`, { headers });
    expect(appointmentResponse.status()).toBe(200);
    const appointment = await appointmentResponse.json();
    const contextResponse = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/encounters/appointment-context/?business_id=${appointment.business}&appointment_id=${id}`, { headers });
    expect(contextResponse.status()).toBe(200);
    const context = await contextResponse.json();
    const recovery = language === "en" && width === 390;
    const fixture = (command: string) => execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", command, String(id)], { env: process.env, windowsHide: true, stdio: "pipe" });
    if (recovery) fixture("client-entry-pages");
    await page.goto(`/app/clients/${context.patient.client_id}`);
    const profile = page.getByTestId("patient-administration");
    const branch = profile.getByRole("combobox", { name: t["medical.branch"] });
    const listRoute = "**/api/medical/encounters/client-appointments/**";
    if (recovery) await page.route(listRoute, route => route.fulfill({ status: 503, json: {} }));
    await branch.click();
    await page.getByRole("option", { name: "First", exact: true }).click();
    if (recovery) {
      await expect(profile.getByText(t["actions.errorTemporary"], { exact: true })).toBeVisible();
      await page.unroute(listRoute);
      await profile.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    const entry = page.getByTestId("client-clinical-entry");
    if (recovery) await entry.getByRole("button", { name: t["medical.clinical.older"], exact: true }).click();
    const picker = entry.getByRole("combobox", { name: t["medical.clientEntry.appointment"] });
    await picker.click();
    await expect(page.getByRole("option")).toHaveCount(recovery ? 3 : 2);
    await page.getByRole("option").last().click();
    const open = entry.getByRole("button", { name: t["medical.clinical.open"], exact: true });
    await expect(open).toBeVisible();
    if (recovery) {
      await entry.getByRole("button", { name: t["medical.clinical.newest"], exact: true }).click();
      await expect(open).toHaveCount(0);
      await entry.getByRole("button", { name: t["medical.clinical.older"], exact: true }).click();
      await picker.click();
      await expect(page.getByRole("option")).toHaveCount(3);
      await page.getByRole("option").last().click();
      await expect(open).toBeVisible();
    }
    await entry.screenshot({ path: info.outputPath("client-clinical-picker.png") });
    await open.click();
    const workspace = page.getByTestId("clinical-workspace");
    await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`CLIENT-${id}`);
    await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
    await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
    await workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true }).fill(`Synthetic client entry ${id}`);
    await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(workspace.getByText(t["common.saved"], { exact: true })).toBeVisible();
    if (recovery) {
      const complaint = workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true });
      await complaint.fill("Synthetic unsaved client note");
      await page.keyboard.press("Escape");
      await page.getByTestId("clinical-unsaved").getByRole("button", { name: t["medical.clinical.continueEditing"], exact: true }).click();
      await expect(complaint).toHaveValue("Synthetic unsaved client note");
      await complaint.fill(`Synthetic client entry ${id}`);
    }
    await workspace.getByRole("tab", { name: t["medical.overview.title"], exact: true }).click();
    await expect(workspace.getByTestId("clinical-overview")).toBeVisible();
    await workspace.screenshot({ path: info.outputPath("client-clinical-workspace.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-workspace"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(workspace).not.toBeVisible();
    await expect(open).toBeFocused();
    if (recovery) await page.route("**/api/medical/encounters/appointment-context/**", route => route.fulfill({ status: 403, json: {} }));
    await open.click();
    if (recovery) {
      await expect(workspace.getByText(t["medical.denied"], { exact: true })).toBeVisible();
      await expect(workspace.getByRole("tab")).toHaveCount(0);
      await workspace.screenshot({ path: info.outputPath("client-clinical-denied.png") });
      await page.keyboard.press("Escape");
      await expect(workspace).not.toBeVisible();
      fixture("client-entry-empty");
      await branch.click();
      await page.getByRole("option", { name: "Second", exact: true }).click();
      await expect(entry).toHaveCount(0);
      await branch.click();
      await page.getByRole("option", { name: "First", exact: true }).click();
      await expect(entry.getByText(t["medical.clientEntry.empty"], { exact: true })).toBeVisible();
      await expect(entry.getByRole("combobox")).toHaveCount(0);
      await entry.screenshot({ path: info.outputPath("client-clinical-empty.png") });
    } else {
      await expect(workspace.getByRole("tab", { name: t["medical.overview.title"], exact: true })).toHaveAttribute("aria-selected", "true");
      await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
      await expect(workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toHaveValue(`Synthetic client entry ${id}`);
    }
  });
}
