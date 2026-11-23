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
  test(`clinical representatives ${language} ${width}: current scope and readonly authority`, async ({ page }, info) => {
    test.setTimeout(90_000);
    const t = { ru, kk, en }[language];
    const fixture = (command: string, count = 4) => execFileSync(process.env.E2E_PYTHON!,
      ["e2e/clinical-runtime.py", command, String(id), String(count)], { env: process.env, windowsHide: true, stdio: "pipe" });
    fixture("historical-orders-context");
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await page.locator('form button[type="submit"]').click();
    const token = (await (await login).json()).access;
    await expect(page).toHaveURL(/\/app\//);
    await page.goto("/app/calendar");
    await page.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    const row = page.getByTestId(/^participation-row-/).filter({ hasText: `Synthetic clinical patient ${id}` });
    await row.getByRole("button", { name: t["medical.overview.title"], exact: true }).click();
    const overview = page.getByTestId("clinical-overview");
    const open = overview.getByRole("button", { name: t["medical.representatives"], exact: true });
    const recovery = language === "en" && width === 390;
    const route = "**/api/medical/encounters/representatives/**";
    if (recovery) await page.route(route, request => request.fulfill({ status: 503, json: {} }));
    await open.click();
    const modal = page.getByTestId("clinical-representatives");
    if (recovery) {
      await expect(modal.getByText(t["actions.errorTemporary"], { exact: true })).toBeVisible();
      await page.unroute(route);
      await modal.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(modal.getByText(t["medical.repEmpty"], { exact: true })).toBeVisible();
    fixture("clinical-representatives-populate", recovery ? 26 : 4);
    await modal.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(modal.locator("li")).toHaveCount(recovery ? 25 : 4);
    await expect(modal.getByRole("button", { name: t["medical.repAdd"], exact: true })).toHaveCount(0);
    await expect(modal.getByRole("button", { name: t["medical.repRevoke"], exact: true })).toHaveCount(0);
    await modal.screenshot({ path: info.outputPath("clinical-representatives.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-representatives"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (recovery) {
      await modal.getByRole("button", { name: t["medical.repNext"], exact: true }).click();
      await expect(modal.locator("li")).toHaveCount(1);
      await modal.getByRole("button", { name: t["medical.repPrevious"], exact: true }).click();
      await expect(modal.locator("li")).toHaveCount(25);
      fixture("historical-orders-end");
      await modal.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(modal.getByText(t["medical.denied"], { exact: true })).toBeVisible();
      await expect(modal.locator("li")).toHaveCount(0);
      await modal.screenshot({ path: info.outputPath("clinical-representatives-denied.png") });
    }
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
    await expect(open).toBeFocused();
    const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${id}/`, { headers: { Authorization: `Bearer ${token}` } });
    expect(response.ok()).toBe(true);
    const appointment = await response.json();
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await page.getByTestId("clinical-appointment-entry").getByRole("button", { name: t["medical.clinical.open"], exact: true }).click();
    await page.getByTestId("clinical-workspace").getByRole("tab", { name: t["medical.overview.title"], exact: true }).click();
    await open.click();
    await expect(modal.locator("li")).toHaveCount(recovery ? 25 : 4);
    await page.keyboard.press("Escape");
    await expect(open).toBeFocused();
  });
}
