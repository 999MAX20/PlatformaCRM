import { expect, test } from "@playwright/test";
import path from "node:path";

for (const language of ["ru", "kk", "en"]) {
  test(`service form retains input after failure and saves with an accessible toast ${language}`, async ({ page }) => {
    await page.setViewportSize({ width: language === "ru" ? 1440 : 390, height: 1000 });
    await page.addInitScript(language => localStorage.setItem("ai_smb_language", language), language);
    await page.goto("/login");
    await page.locator('form input[type="email"]').fill("business_owner@example.com");
    await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/app/);
    await page.goto("/app/services");
    await page.locator('[data-testid="service-name"]:visible').first().click();
    const dialog = page.getByTestId("service-edit-modal");
    await expect(dialog).toBeVisible();
    const description = dialog.locator('textarea[name="description"]');
    const original = await description.inputValue();
    const edited = `Alert verification ${language} ${Date.now()}`;
    await description.fill(edited);
    let attempts = 0;
    await page.route(/\/api\/services\/\d+\/$/, async route => {
      if (route.request().method() !== "PATCH") return route.continue();
      attempts++;
      if (attempts === 1) return route.fulfill({ status: 503, json: { code: "temporary_service_failure", request_id: `alerts-${language}`, retryable: true } });
      return route.continue();
    });
    const submit = dialog.locator('button[form="service-edit-form"]');
    await submit.click();
    const failure = dialog.getByTestId("inline-fallback");
    await expect(failure).toBeVisible();
    await expect(description).toHaveValue(edited);
    await expect(page.getByTestId("action-feedback")).toHaveCount(0);
    expect(await failure.evaluate(node => getComputedStyle(node).backgroundColor)).toBe("rgb(163, 59, 53)");
    await page.screenshot({ path: path.resolve(`../output/alert-components-20261102/app-error-${language}.png`) });
    await submit.click();
    const toast = dialog.getByTestId("action-feedback");
    await expect(toast).toBeVisible();
    await expect(failure).toHaveCount(0);
    expect(attempts).toBe(2);
    expect(await toast.evaluate(node => getComputedStyle(node).backgroundColor)).toBe("rgb(0, 122, 89)");
    const close = toast.getByRole("button");
    await description.focus();
    for (let i = 0; i < 16 && !(await close.evaluate(node => node === document.activeElement)); i++) await page.keyboard.press("Tab");
    await expect(close).toBeFocused();
    await expect(close).toBeInViewport();
    await page.screenshot({ path: path.resolve(`../output/alert-components-20261102/app-success-${language}.png`) });
    await page.keyboard.press("Enter");
    await expect(toast).toHaveCount(0);
    expect(await dialog.evaluate(node => node.contains(document.activeElement))).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await description.fill(original);
    await submit.click();
    await expect(toast).toBeVisible();
  });
}
