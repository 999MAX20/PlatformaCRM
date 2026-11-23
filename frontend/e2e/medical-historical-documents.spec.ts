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
  test(`historical documents ${language} ${width}: participation exact versions`, async ({ page }, info) => {
    test.setTimeout(90_000);
    const t = { ru, kk, en }[language];
    const fixture = (command: string, count = 1) => execFileSync(process.env.E2E_PYTHON!,
      ["e2e/clinical-runtime.py", command, String(id), String(count)], { env: process.env, windowsHide: true, stdio: "pipe" });
    fixture("historical-orders-context");
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/app\//);
    await page.goto("/app/calendar");
    await page.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    const row = page.getByTestId(/^participation-row-/).filter({ hasText: `Synthetic clinical patient ${id}` });
    await row.getByRole("button", { name: t["medical.clinical.history"], exact: true }).click();
    const clinical = page.getByTestId("clinical-history");
    await clinical.locator("ul > li > button").first().click();
    await expect(clinical.getByTestId("clinical-version")).toBeVisible();
    const open = clinical.getByRole("button", { name: t["medical.documents.title"], exact: true });
    const recovery = language === "en" && width === 390;
    const route = "**/api/medical/documents/**";
    if (recovery) await page.route(route, request => new URL(request.request().url()).pathname === "/api/medical/documents/"
      ? request.fulfill({ status: 503, json: {} }) : request.continue());
    await open.click();
    const modal = page.getByTestId("historical-documents");
    const documents = modal.getByTestId("medical-documents");
    if (recovery) {
      await expect(documents.getByText(t["actions.errorTemporary"], { exact: true })).toBeVisible();
      await page.unroute(route);
      await documents.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(documents.getByText(t["medical.documents.empty"], { exact: true })).toBeVisible();
    await expect(documents.getByRole("button", { name: t["medical.documents.create"], exact: true })).toHaveCount(0);
    fixture("historical-documents-populate", recovery ? 22 : 1);
    await documents.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(documents.locator("ul > li")).toHaveCount(recovery ? 20 : 1);
    if (recovery) {
      await documents.getByRole("button", { name: t["medical.templates.more"], exact: true }).click();
      await expect(documents.locator("ul > li")).toHaveCount(22);
    }
    const selected = documents.locator("ul > li").last().getByRole("button");
    await selected.scrollIntoViewIfNeeded();
    await modal.screenshot({ path: info.outputPath("historical-document-list.png") });
    await selected.click();
    const detail = documents.getByTestId("medical-document-detail");
    await expect(detail.getByTestId("medical-document-text")).toHaveText("Synthetic historical document 0 v2");
    await expect(detail.getByRole("button", { name: t["medical.documents.edit"], exact: true })).toHaveCount(0);
    await detail.getByRole("button", { name: t["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
    await expect(detail.getByTestId("medical-document-text")).toHaveText("Synthetic historical document 0 v1");
    await modal.screenshot({ path: info.outputPath("historical-document-version.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="historical-documents"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await documents.getByRole("button", { name: t["medical.documents.back"], exact: true }).click();
    await expect(selected).toBeFocused();
    if (recovery) {
      fixture("historical-orders-end");
      await documents.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(documents.getByText(t["medical.denied"], { exact: true })).toBeVisible();
      await expect(documents.locator("li")).toHaveCount(0);
      await modal.screenshot({ path: info.outputPath("historical-document-denied.png") });
    }
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
    await expect(open).toBeFocused();
  });
}
