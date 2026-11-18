import { test, expect } from "@playwright/test";
import { integrations as ru } from "../src/lib/i18n/ru/integrations";
import { integrations as kk } from "../src/lib/i18n/kk/integrations";
import { integrations as en } from "../src/lib/i18n/en/integrations";

for (const [lang, dictionary] of Object.entries({ ru, kk, en })) {
  test(`${lang}: history count, processing and recoverable failure`, async ({ page }, info) => {
    let failed = true;
    await page.route("http://127.0.0.1:6027/api/**", async route => {
      if (route.request().method() === "POST") {
        expect(route.request().postDataJSON()).toEqual({ action: "retry_events" });
        failed = false;
        return route.fulfill({ json: { ok: true } });
      }
      return route.fulfill({ json: { available: true, status: "connected", channel_status: "active",
        phone_number: "+77010000000", onboarding_type: "WHATSAPP_BUSINESS_APP", failed_events: failed ? 1 : 0,
        history: { messages: 1234, pending_events: failed ? 0 : 2, failed_events: failed ? 1 : 0 } } });
    });
    await page.goto(`/e2e-ycloud/fixture.html?lang=${lang}`);
    const count = dictionary["integrations.ycloud.historyCount"].replace("{count}", "1234");
    await expect(page.getByText(count, { exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toContainText(dictionary["integrations.ycloud.needsAttention"]);
    await page.getByRole("button", { name: { ru: "Повторить", kk: "Қайталау", en: "Retry" }[lang], exact: true }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByText(dictionary["integrations.ycloud.historyPending"], { exact: false })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${lang}-history.png`), fullPage: true });
  });
}

test("new channel can enter YCloud and return without modifying a connected channel", async ({ page }) => {
  await page.route("http://127.0.0.1:6027/api/**", route => {
    expect(route.request().method()).toBe("GET");
    const isYcloud = route.request().url().includes("/ycloud/");
    return route.fulfill({ json: isYcloud
      ? { available: true, status: "not_connected", channel_status: "draft", onboarding_type: "WHATSAPP_BUSINESS_PLATFORM" }
      : { phone_number_id_configured: false, access_token_configured: false } });
  });
  await page.goto("/e2e-ycloud/fixture.html?lang=en&entry=1");
  await page.getByRole("button", { name: "Connect via YCloud", exact: true }).click();
  await expect(page.getByTestId("ycloud-setup")).toBeVisible();
  await page.getByRole("button", { name: "Another connection method", exact: true }).click();
  await expect(page.getByTestId("ycloud-setup")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Connect via YCloud", exact: true })).toBeVisible();
  await page.goto("/e2e-ycloud/fixture.html?lang=en&entry=1&paused=1");
  await expect(page.getByRole("button", { name: "Connect via YCloud", exact: true })).toHaveCount(0);
  await page.goto("/e2e-ycloud/fixture.html?lang=en&entry=1&readonly=1");
  await expect(page.getByRole("button", { name: "Connect via YCloud", exact: true })).toHaveCount(0);
});
