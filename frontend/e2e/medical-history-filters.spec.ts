import { test, expect } from "@playwright/test";
import { openClinicalWorkspace } from "./clinical-card-navigation";
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
  test(`history filters ${language} ${width}: server filters and retained exact version`, async ({ page }, info) => {
    test.setTimeout(120_000);
    const t = { ru, kk, en }[language];
    const fixture = (command: string) => execFileSync(process.env.E2E_PYTHON!,
      ["e2e/clinical-runtime.py", command, String(id)], { env: process.env, windowsHide: true, stdio: "pipe" });
    fixture("historical-orders-context");
    fixture("history-filters-populate");
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    await page.locator('form button[type="submit"]').click();
    const token = (await (await login).json()).access;
    await expect(page).toHaveURL(/\/app\//);
    const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/encounters/workspace/?business_id=1&patient_id=${id}&appointment_id=${id}`,
      { headers: { Authorization: `Bearer ${token}` } });
    expect(response.status()).toBe(200);
    const metadata = await response.json();
    const finalized = metadata.encounters.find((item: { state: string }) => item.state === "finalized");
    await page.goto("/app/calendar");
    const entry = page.getByRole("button", { name: t["medical.participation.title"], exact: true });
    await entry.click();
    const row = page.getByTestId(/^participation-row-/).filter({ hasText: `Synthetic clinical patient ${id}` });
    const historyOpen = row.getByRole("button", { name: t["medical.clinical.history"], exact: true });
    await historyOpen.click();
    const history = page.getByTestId("clinical-history");
    const filters = history.getByTestId("clinical-history-filters");
    const rows = history.locator("ul > li > button");
    await expect(rows).toHaveCount(2);
    const select = async (label: string, option: string) => {
      await filters.getByRole("combobox", { name: label }).click();
      await page.getByRole("option", { name: option, exact: true }).click();
    };
    await select(t["medical.branch"], "Synthetic history branch");
    await select(t["medical.clinical.currentAuthor"], finalized.author_name || t["medical.clinical.authorUnknown"]);
    await select(t["appointment.status"], t["medical.clinical.state.finalized"]);
    await filters.getByLabel(t["timeline.dateFrom"], { exact: true }).fill("2026-10-11");
    await filters.getByLabel(t["timeline.dateTo"], { exact: true }).fill("2026-10-11");
    await filters.getByRole("button", { name: t["crmFilters.apply"], exact: true }).click();
    await expect(rows).toHaveCount(1);
    await rows.first().click();
    await expect(history.getByTestId("clinical-version").getByText("Synthetic other branch finalized", { exact: true })).toBeVisible();
    await filters.screenshot({ path: info.outputPath("history-filters.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-history"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await row.getByRole("button", { name: t["medical.overview.title"], exact: true }).click();
    await historyOpen.click();
    await expect(filters.getByLabel(t["timeline.dateFrom"], { exact: true })).toHaveValue("2026-10-11");
    await expect(history.getByTestId("clinical-version").getByText("Synthetic other branch finalized", { exact: true })).toBeVisible();
    await filters.getByRole("button", { name: t["common.reset"], exact: true }).click();
    await select(t["appointment.status"], t["medical.clinical.state.draft"]);
    await filters.getByRole("button", { name: t["crmFilters.apply"], exact: true }).click();
    await expect(rows).toHaveCount(1);
    await rows.first().click();
    const versions = history.getByTestId("clinical-revisions");
    await expect(versions.getByTestId("clinical-version").getByText("Synthetic selected history v2", { exact: true })).toBeVisible();
    await versions.getByRole("button", { name: new RegExp(`${t["medical.clinical.revision"]} 1\\b`) }).click();
    await expect(versions.getByTestId("clinical-version").getByText("Synthetic selected history v2", { exact: true })).toHaveCount(0);
    await page.keyboard.press("Escape");
    await entry.click();
    await historyOpen.click();
    await expect(versions.getByRole("button", { name: new RegExp(`${t["medical.clinical.revision"]} 1\\b`) })).toHaveAttribute("aria-pressed", "true");
    await versions.screenshot({ path: info.outputPath("history-restored-version.png") });
    const recovery = language === "en" && width === 390;
    const route = "**/api/medical/encounters/workspace/**";
    if (recovery) await page.route(route, request => request.fulfill({ status: 503, json: {} }));
    await filters.getByLabel(t["timeline.dateFrom"], { exact: true }).fill("2030-01-01");
    await filters.getByRole("button", { name: t["crmFilters.apply"], exact: true }).click();
    if (recovery) {
      await expect(history.getByText(t["actions.errorTemporary"], { exact: true })).toBeVisible();
      await expect(filters.getByLabel(t["timeline.dateFrom"], { exact: true })).toHaveValue("2030-01-01");
      await page.unroute(route);
      await history.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(history.getByText(t["medical.clinical.historyEmpty"], { exact: true })).toBeVisible();
    await filters.getByRole("button", { name: t["common.reset"], exact: true }).click();
    await expect(rows).toHaveCount(2);
    if (recovery) {
      fixture("historical-orders-end");
      await filters.getByRole("button", { name: t["crmFilters.apply"], exact: true }).click();
      await expect(history).not.toBeVisible();
      await expect(page.getByText(t["medical.denied"], { exact: true })).toBeVisible();
    }
    await page.keyboard.press("Escape");
    const appointmentResponse = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${id}/`, { headers: { Authorization: `Bearer ${token}` } });
    const appointment = await appointmentResponse.json();
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}&view=day`);
    await openClinicalWorkspace(page);
    const workspace = page.getByTestId("clinical-workspace");
    await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
    await select(t["appointment.status"], t["medical.clinical.state.draft"]);
    await filters.getByRole("button", { name: t["crmFilters.apply"], exact: true }).click();
    await expect(rows).toHaveCount(1);
    await rows.first().click();
    await versions.getByRole("button", { name: new RegExp(`${t["medical.clinical.revision"]} 1\\b`) }).click();
    await workspace.getByRole("tab", { name: t["medical.overview.title"], exact: true }).click();
    await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
    await expect(versions.getByRole("button", { name: new RegExp(`${t["medical.clinical.revision"]} 1\\b`) })).toHaveAttribute("aria-pressed", "true");
    await page.keyboard.press("Escape");
    await openClinicalWorkspace(page, true);
    await expect(versions.getByRole("button", { name: new RegExp(`${t["medical.clinical.revision"]} 1\\b`) })).toHaveAttribute("aria-pressed", "true");
  });
}
