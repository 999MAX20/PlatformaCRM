import { test, expect } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.skip(process.env.E2E_MEDICAL_ROLLOUT !== "1", "Requires the isolated profile rollout fixture");

for (const width of [1440, 390]) {
  for (const [role, email] of [
    ["doctor", "medical-role-doctor@example.test"],
    ["owner", "medical-role-owner@example.test"],
    ["other-industry", "rollout-other@example.test"],
  ]) {
    test(`medical rollout ${role} ${width}: existing settings entry respects access`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
      await page.goto("/login");
      await page.locator('input[name="email"]').fill(email);
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const authenticated = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
      await page.locator('form button[type="submit"]').click();
      const token = (await (await authenticated).json()).access;
      await expect(page).toHaveURL(/\/app\//);
      const access = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/document-templates/workspace-access/?business_id=1`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(access.status()).toBe(role === "doctor" ? 200 : 403);
      await page.goto("/app/settings#medical-templates");
      await expect(page.getByTestId("settings-workspace-ready")).toBeVisible();
      const workspace = page.getByTestId("medical-template-workspace");
      if (role === "doctor") {
        await expect(workspace).toBeVisible();
        const create = workspace.getByRole("button", { name: ru["medical.templates.create"], exact: true });
        await create.click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(page.getByRole("dialog")).toHaveCount(0);
        await expect(create).toBeFocused();
      } else {
        await expect(page.getByText(ru["common.loadingData"], { exact: true })).toHaveCount(0);
        await expect(workspace).toHaveCount(0);
        await expect(page.locator('a[href="#medical-templates"]')).toHaveCount(0);
        if (width === 390) {
          const navigation = page.getByRole("combobox", { name: new RegExp(ru["settings.navigationTitle"]) });
          await navigation.click();
          await expect(page.getByRole("option", { name: ru["settings.section.medical-templates"], exact: true })).toHaveCount(0);
          await page.keyboard.press("Escape");
        }
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath("rollout-access.png") });
    });
  }
}
