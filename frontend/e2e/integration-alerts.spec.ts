import { expect, test } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  for (const width of [390, 1440]) {
    test(`Telegram disabled cause, persistent error and successful retry ${language} ${width}`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
      let reason = "Telegram integration is disabled.", ok = false, requests = 0;
      await page.route("**/api/bot-channels/2/**", route => {
        if (route.request().method() === 'POST') { requests++;return route.fulfill({ json: { ok, reason } }); }
        return route.fulfill({ json: { status: ok ? 'active' : 'error', token_configured: true, token_verified: true, webhook_configured: true, last_error: ok ? '' : reason } });
      });
      await page.goto('/e2e/fixtures/integration-alerts.html');
      const dialog = page.getByRole('dialog');
      await expect(dialog.getByText(copy['integrations.error.integrationDisabled'], { exact: true })).toBeVisible();
      await dialog.getByRole('button', { name: copy['integrations.telegram.testConnection'], exact: true }).click();
      const toast = page.getByTestId('action-feedback');
      await expect(toast).toContainText(copy['integrations.error.integrationDisabled']);
      await expect(toast).not.toContainText(copy['integrations.error.actionRequired']);
      await page.screenshot({ path: info.outputPath(`telegram-${language}-${width}.png`) });
      await toast.getByRole('button', { name: copy['common.close'], exact: true }).click();
      await expect(toast).toHaveCount(0);
      await expect(dialog.getByText(copy['integrations.error.integrationDisabled'], { exact: true })).toBeVisible();
      reason = 'Telegram bot token is missing.';
      await dialog.getByRole('button', { name: copy['integrations.telegram.testConnection'], exact: true }).click();
      await expect(toast).toContainText(copy['integrations.error.credentialsMissingManage']);
      await toast.getByRole('button', { name: copy['common.close'], exact: true }).click();
      await expect(toast).toHaveCount(0);
      ok = true;
      await dialog.getByRole('button', { name: copy['integrations.telegram.testConnection'], exact: true }).click();
      await expect(toast).toContainText(copy['integrations.telegram.connectionChecked']);
      await expect(dialog.getByText(copy['integrations.error.credentialsMissingManage'], { exact: true })).toHaveCount(0);
      expect(requests).toBe(3);
    });
  }
  test(`read-only user receives permitted guidance without mutation ${language}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    let writes = 0;
    await page.route('**/api/bot-channels/2/**', route => {
      if (route.request().method() !== 'GET') writes++;
      return route.fulfill({ json: { status: 'error', token_configured: false, token_verified: false, webhook_configured: true, last_error: 'Telegram bot token is missing.' } });
    });
    await page.goto('/e2e/fixtures/integration-alerts.html?readonly');
    await expect(page.getByText(copy['integrations.error.credentialsMissingReadOnly'], { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: copy['integrations.telegram.testConnection'], exact: true })).toBeDisabled();
    expect(writes).toBe(0);
  });
}
