import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
for (const language of ["ru", "kk", "en"] as const) {
  for (const width of [1440, 390]) {
    test(`patient registration ${language} ${width}: search then atomic client and profile`, async ({ page }, info) => {
      const t = { ru, kk, en }[language];
      const recovery = language === "ru" && width === 1440;
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("patient-reception@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await page.locator('form button[type="submit"]').click();
      const headers = { Authorization: `Bearer ${(await (await login).json()).access}` };
      await expect(page).toHaveURL(/\/app\//); await page.goto("/app/clients");
      await page.getByTestId("patient-search-open").click();
      const dialog = page.getByRole("dialog");
      await dialog.getByRole("combobox", { name: new RegExp(t["medical.branch"]) }).click();
      await page.getByRole("option", { name: "First", exact: true }).click();
      const name = `New synthetic ${language} ${width} ${Date.now()}`;
      await dialog.getByTestId("patient-search-query").fill(name);
      await dialog.getByRole("button", { name: t["common.search"], exact: true }).click();
      await expect(dialog.getByText(t["medical.search.empty"], { exact: true })).toBeVisible();
      await dialog.getByRole("button", { name: t["medical.registration.create"], exact: true }).click();
      const form = dialog.getByTestId("patient-registration");
      await expect(form.getByRole("textbox", { name: t["medical.fullName"], exact: true })).toHaveValue(name);
      await form.getByRole("textbox", { name: t["medical.search.phone"], exact: true }).fill(recovery ? "+77000000001" : `+7${String(Date.now()).slice(-10)}`);
      await form.getByRole("textbox", { name: t["medical.address"], exact: true }).fill("Synthetic private registration address");
      const iin = String(Date.now()).slice(-12);
      await form.getByRole("textbox", { name: t["medical.iin"], exact: true }).fill(iin);
      const create = form.getByRole("button", { name: t["medical.registration.create"], exact: true });
      const keys: string[] = [];
      if (recovery) {
        page.once("dialog", message => message.dismiss()); await page.keyboard.press("Escape"); await expect(dialog).toBeVisible();
        await page.route("**/api/medical/patients/register/", route => {
          keys.push(route.request().headers()["idempotency-key"]);
          return keys.length === 1 ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue();
        });
        await create.click(); await expect(form.getByRole("alert")).toBeVisible();
        await expect(form.getByRole("textbox", { name: t["medical.iin"], exact: true })).toHaveValue(iin);
        const conflict = page.waitForResponse(r => r.url().endsWith("/register/") && r.request().method() === "POST");
        await create.click(); expect((await conflict).status()).toBe(409);
        await expect(form.getByText(t["medical.registration.matches"], { exact: true })).toBeVisible();
        await expect(create).toBeDisabled();
        await form.getByRole("checkbox", { name: t["medical.registration.separate"], exact: true }).check();
        expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
      }
      await dialog.screenshot({ path: info.outputPath("registration-form.png") });
      const created = page.waitForResponse(r => r.url().endsWith("/register/") && r.request().method() === "POST");
      await create.click();
      const response = await created; expect(response.status()).toBe(201);
      const result = await response.json();
      await expect(page).toHaveURL(new RegExp(`/app/clients/${result.client_id}$`));
      const medical = page.getByTestId("patient-administration");
      await medical.getByRole("combobox", { name: new RegExp(t["medical.branch"]) }).click();
      await page.getByRole("option", { name: "First", exact: true }).click();
      await expect(medical.getByText(t["medical.unverified"], { exact: true })).toBeVisible();
      const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers, params: { q: name } });
      expect((await clients.json()).results.filter((item: { full_name: string }) => item.full_name === name)).toHaveLength(1);
      expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic private registration address");
      expect(page.url()).not.toContain(iin);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      if (recovery) { expect(keys).toHaveLength(3); expect(keys[0]).toBe(keys[1]); expect(keys[2]).not.toBe(keys[1]); }
    });
  }
}
