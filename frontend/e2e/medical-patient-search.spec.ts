import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { execFileSync } from "node:child_process";

requireIsolatedEnvironment();
for (const language of ["ru", "kk", "en"] as const) {
  for (const width of [1440, 390]) {
    test(`patient search ${language} ${width}: permitted results, private POST and existing card`, async ({ page }, info) => {
      const t = { ru, kk, en }[language];
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("patient-reception@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      await page.locator('form button[type="submit"]').click();
      await expect(page).toHaveURL(/\/app\//);
      await page.goto("/app/clients");
      const opener = page.getByTestId("patient-search-open");
      await opener.focus(); await page.keyboard.press("Enter");
      let dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0); await expect(opener).toBeFocused();
      await opener.click(); dialog = page.getByRole("dialog");
      const input = dialog.getByTestId("patient-search-query");
      const query = `Synthetic ${language} ${width === 1440 ? "desktop" : "mobile"}`;
      await input.fill(query);
      const search = dialog.getByRole("button", { name: t["common.search"], exact: true });
      if (language === "ru" && width === 1440) {
        let fail = true;
        await page.route("**/api/medical/patients/resolve/", async route => {
          if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
          return route.continue();
        });
        await search.click();
        await expect(dialog.getByRole("button", { name: t["common.retry"], exact: true })).toBeVisible();
        await expect(input).toHaveValue(query);
        await dialog.screenshot({ path: info.outputPath("search-recovery.png") });
        await dialog.getByRole("button", { name: t["common.retry"], exact: true }).click();
      } else await search.click();
      const results = dialog.getByTestId("patient-search-results");
      await expect(results.getByText(query, { exact: true })).toBeVisible();
      await expect(results.getByText(t["medical.search.possible"], { exact: true })).toBeVisible();
      expect(page.url()).not.toContain(query);
      expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if (language === "ru" && width === 1440) {
        expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
      }
      await dialog.screenshot({ path: info.outputPath("search-results.png") });
      await input.fill("Missing synthetic patient 999");
      const response = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/resolve/"));
      await search.click();
      const found = await response;
      expect(found.status()).toBe(200); expect(found.request().method()).toBe("POST");
      expect(new URL(found.url()).search).toBe("");
      expect(found.headers()["cache-control"]).toContain("no-store");
      await expect(results.getByText(t["medical.search.empty"], { exact: true })).toBeVisible();
      await input.fill(query); await search.click();
      await results.getByRole("button", { name: `${t["common.open"]}: ${query}`, exact: true }).click();
      await expect(page).toHaveURL(/\/app\/clients\/\d+$/);
      await expect(page.getByTestId("patient-administration")).toBeVisible();
    });
  }
}

for (const width of [1440, 390]) {
  test(`patient search boundaries ${width}: pagination, archive, family contacts and revoked access`, async ({ page }, info) => {
    test.skip(process.env.E2E_PATIENT_SEARCH !== "1", "Requires isolated search pagination fixtures");
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("patient-reception@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/app\//);
    await page.goto("/app/clients"); await page.getByTestId("patient-search-open").click();
    const dialog = page.getByRole("dialog");
    const input = dialog.getByTestId("patient-search-query");
    const search = dialog.getByRole("button", { name: ru["common.search"], exact: true });
    const results = dialog.getByTestId("patient-search-results");
    await input.fill("Search pagination"); await search.click();
    await expect(results.getByRole("listitem")).toHaveCount(25);
    await results.getByRole("button", { name: ru["medical.search.more"], exact: true }).click();
    await expect(results.getByRole("listitem")).toHaveCount(27);
    await expect(results.getByRole("button", { name: ru["medical.search.more"], exact: true })).toHaveCount(0);
    await dialog.getByRole("checkbox").check(); await search.click();
    await results.getByRole("button", { name: ru["medical.search.more"], exact: true }).click();
    await expect(results.getByRole("listitem")).toHaveCount(28);
    await expect(results.getByText(ru["clients.card.archived"], { exact: true })).toBeVisible();
    await dialog.getByRole("combobox", { name: new RegExp(ru["medical.search.field"]) }).click();
    await page.getByRole("option", { name: ru["medical.search.phone"], exact: true }).click();
    await input.fill("+77000000001"); await search.click();
    await expect(results.getByRole("listitem")).toHaveCount(2);
    await expect(results.getByText(ru["medical.search.possible"], { exact: true })).toHaveCount(2);
    await dialog.screenshot({ path: info.outputPath("family-matches.png") });
    if (width === 390) {
      execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "revoke"], { env: process.env, stdio: "pipe" });
      try {
        await search.click();
        await expect(dialog.getByText(ru["medical.denied"], { exact: true })).toBeVisible();
        await expect(input).toHaveCount(0); await expect(results).toHaveCount(0);
        await dialog.screenshot({ path: info.outputPath("search-denied.png") });
      } finally {
        execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "restore-search"], { env: process.env, stdio: "pipe" });
      }
    }
  });
}
