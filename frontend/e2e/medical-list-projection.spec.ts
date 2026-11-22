import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
for (const language of ["ru", "kk", "en"] as const) {
  for (const width of [1440, 390]) {
    test(`medical list ${language} ${width}: scoped status and current access`, async ({ page }, info) => {
      const t = { ru, kk, en }[language];
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("patient-reception@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      await page.locator('form button[type="submit"]').click();
      await expect(page).toHaveURL(/\/app\//); await page.goto("/app/clients");
      const controls = page.getByTestId("medical-list-controls");
      const branch = controls.getByRole("combobox", { name: new RegExp(t["medical.list.branch"]) });
      await branch.focus(); await page.keyboard.press("Enter");
      await page.getByRole("option", { name: "First", exact: true }).click();
      const search = page.getByTestId("clients-search-input");
      await search.fill(`Correction fixture ${language} ${width}`);
      const workspace = page.getByTestId("clients-workspace-ready");
      const present = workspace.getByText(new RegExp(t["medical.list.present"])).filter({ visible: true });
      await expect(present).toHaveCount(1);
      if (language === "ru" && width === 1440) {
        const refresh = controls.getByRole("button", { name: t["medical.clinical.reload"], exact: true });
        await refresh.focus();
        const response = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/list-projection/") && r.request().method() === "POST");
        await page.keyboard.press("Enter"); await response;
        await expect(present).toHaveCount(1); await expect(refresh).toBeFocused();
      }
      if (width === 1440) await expect(page.getByRole("columnheader", { name: t["medical.list.status"], exact: true })).toBeVisible();
      await expect(page.locator("body")).not.toContainText("Synthetic private address");
      expect((await new AxeBuilder({ page }).include('[data-testid="clients-workspace-ready"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await workspace.screenshot({ path: info.outputPath("medical-list.png") });
      if (language === "ru" && width === 390) {
        let fail = true;
        await page.route("**/api/medical/patients/list-projection/", route => {
          if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
          return route.continue();
        });
        await controls.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
        await expect(controls.getByRole("button", { name: t["common.retry"], exact: true })).toBeVisible();
        await expect(present).toHaveCount(0);
        await controls.getByRole("button", { name: t["common.retry"], exact: true }).click();
        await expect(present).toHaveCount(1);
        execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "revoke"], { env: process.env, stdio: "pipe" });
        try {
          await controls.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
          await expect(controls.getByText(t["medical.denied"], { exact: true })).toBeVisible();
          await expect(present).toHaveCount(0);
          await workspace.screenshot({ path: info.outputPath("medical-list-denied.png") });
        } finally {
          execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "restore-search"], { env: process.env, stdio: "pipe" });
        }
      }
      await search.fill("Search pagination 00");
      if (!(language === "ru" && width === 390)) {
        await expect(workspace.getByText(new RegExp(t["medical.list.absent"])).filter({ visible: true })).toBeVisible();
      }
      const opener = page.getByTestId(width === 1440 ? "client-row-action-open" : "client-card-action-open");
      await expect(opener.filter({ visible: true })).toHaveCount(1);
      await opener.filter({ visible: true }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
    });
  }
}
