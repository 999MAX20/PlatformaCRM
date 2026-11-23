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
  test(`historical orders ${language} ${width}: participation list and versions`, async ({ page }, info) => {
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
    const open = clinical.getByRole("button", { name: t["medical.orders.title"], exact: true });
    const recovery = language === "en" && width === 390;
    const route = "**/api/medical/orders/**";
    if (recovery) await page.route(route, request => new URL(request.request().url()).pathname === "/api/medical/orders/"
      ? request.fulfill({ status: 503, json: {} }) : request.continue());
    await open.click();
    const modal = page.getByTestId("historical-orders");
    const orders = modal.getByTestId("medical-orders");
    if (recovery) {
      await expect(orders.getByText(t["actions.errorTemporary"], { exact: true })).toBeVisible();
      await page.unroute(route);
      await orders.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(orders.getByText(t["medical.orders.empty"], { exact: true })).toBeVisible();
    await expect(orders.getByRole("button", { name: t["medical.orders.create"], exact: true })).toHaveCount(0);
    fixture("historical-orders-populate", recovery ? 22 : 1);
    await orders.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    await expect(orders.locator("ul > li")).toHaveCount(recovery ? 20 : 1);
    if (recovery) {
      await orders.getByRole("button", { name: t["medical.clinical.older"], exact: true }).click();
      await expect(orders.locator("ul > li")).toHaveCount(22);
    }
    await expect(orders.getByRole("button", { name: t["common.edit"], exact: true })).toHaveCount(0);
    const order = orders.locator("li").filter({ hasText: "Synthetic historical order 0 v2" });
    const historyButton = order.getByRole("button", { name: t["medical.orders.history"], exact: true });
    await historyButton.scrollIntoViewIfNeeded();
    await modal.screenshot({ path: info.outputPath("historical-order-list.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="historical-orders"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await historyButton.click();
    const history = page.getByTestId("medical-order-history");
    await expect(history.getByText("Synthetic historical order 0 v1", { exact: true })).toBeVisible();
    await expect(history.getByText("Synthetic historical order 0 v2", { exact: true })).toBeVisible();
    await history.screenshot({ path: info.outputPath("historical-order-versions.png") });
    await page.keyboard.press("Escape");
    await expect(history).not.toBeVisible();
    await expect(historyButton).toBeFocused();
    if (recovery) {
      fixture("historical-orders-end");
      await orders.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(orders.getByText(t["medical.denied"], { exact: true })).toBeVisible();
      await expect(orders.locator("li")).toHaveCount(0);
      await modal.screenshot({ path: info.outputPath("historical-order-denied.png") });
    }
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
    await expect(open).toBeFocused();
  });
}
