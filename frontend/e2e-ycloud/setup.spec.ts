import { test, expect } from "@playwright/test";
import { integrations as ru } from "../src/lib/i18n/ru/integrations";
import { integrations as kk } from "../src/lib/i18n/kk/integrations";
import { integrations as en } from "../src/lib/i18n/en/integrations";

for (const [language, dictionary] of Object.entries({ ru, kk, en })) {
  test(`${language}: keyboard setup, retry, pending and reload`, async ({ page }, info) => {
    const t = (key: string) => dictionary[`integrations.ycloud.${key}`];
    let state = { available: true, status: "not_connected", channel_status: "draft", phone_number: "", expires_at: null, error_code: "", failed_events: 0, onboarding_type: "WHATSAPP_BUSINESS_PLATFORM", expected_phone_number: "" };
    let failStart = true;
    const posts: unknown[] = [];
    await page.route("http://127.0.0.1:6027/api/**", async route => {
      expect(new URL(route.request().url()).origin).toBe("http://127.0.0.1:6027");
      if (route.request().method() === "GET") return route.fulfill({ json: state });
      const body = route.request().postDataJSON(); posts.push(body);
      if (failStart) { failStart = false; return route.fulfill({ status: 503, json: { detail: "Unavailable" } }); }
      if (body.action === "cancel") { state = { ...state, status: "cancelled" }; return route.fulfill({ json: {} }); }
      state = { ...state, status: "pending", onboarding_type: body.onboarding_type, expected_phone_number: body.expected_phone_number };
      return route.fulfill({ json: { onboarding_url: "https://connect.ycloud.com/open/whatsapp/onboard#token=synthetic", expires_at: new Date(Date.now() + 3600000).toISOString() } });
    });
    await page.goto(`/e2e-ycloud/fixture.html?lang=${language}`);
    const mode = page.getByRole("combobox");
    await mode.focus(); await page.keyboard.press("Enter");
    await page.getByRole("option", { name: t("appMode"), exact: true }).click();
    const number = page.getByRole("textbox", { name: new RegExp(`^${t("appNumber")}`) });
    await number.fill("123");
    const start = page.getByRole("button", { name: { ru: "Подключить", kk: "Қосу", en: "Connect" }[language], exact: true });
    await expect(start).toBeDisabled();
    await expect(page.getByText(t("invalidNumber"), { exact: true })).toBeVisible();
    await number.fill("+77010000000");
    await page.keyboard.press("Tab"); await expect(start).toBeFocused();
    await page.screenshot({ path: info.outputPath(`${language}-form.png`), fullPage: true });
    await page.keyboard.press("Enter");
    await expect(page.getByText(t("requestFailed"), { exact: true })).toBeVisible();
    await start.click();
    await expect(page.getByRole("link", { name: t("openSignup") })).toBeVisible();
    expect(posts).toEqual(Array(2).fill({ action: "start", onboarding_type: "WHATSAPP_BUSINESS_APP", expected_phone_number: "+77010000000" }));
    expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("synthetic");
    await page.reload();
    await expect(page.getByText(t("appMode"), { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: t("openSignup") })).toHaveCount(0);
    await expect(mode).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("read-only and unavailable disable setup", async ({ page }) => {
  let available = true;
  await page.route("http://127.0.0.1:6027/api/**", route => {
    expect(route.request().method()).toBe("GET");
    return route.fulfill({ json: { available, status: "not_connected", channel_status: "draft", onboarding_type: "WHATSAPP_BUSINESS_APP", expected_phone_number: "+77010000000" } });
  });
  await page.goto("/e2e-ycloud/fixture.html?lang=en&readonly=1");
  await expect(page.getByRole("combobox")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Connect", exact: true })).toBeDisabled();
  available = false;
  await page.goto("/e2e-ycloud/fixture.html?lang=en");
  await expect(page.getByRole("combobox")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Connect", exact: true })).toBeDisabled();
});

test("loading, default API mode and cancellation", async ({ page }) => {
  let releaseStatus!: () => void;
  const statusReady = new Promise<void>(resolve => { releaseStatus = resolve; });
  let releaseStart!: () => void;
  const startReady = new Promise<void>(resolve => { releaseStart = resolve; });
  let status = "not_connected";
  const posts: unknown[] = [];
  await page.route("http://127.0.0.1:6027/api/**", async route => {
    if (route.request().method() === "GET") {
      await statusReady;
      return route.fulfill({ json: { available: true, status, channel_status: "draft", onboarding_type: "WHATSAPP_BUSINESS_PLATFORM", expected_phone_number: "" } });
    }
    const body = route.request().postDataJSON(); posts.push(body);
    if (body.action === "cancel") { status = "cancelled"; return route.fulfill({ json: {} }); }
    await startReady;
    status = "pending";
    return route.fulfill({ json: { onboarding_url: "https://connect.ycloud.com/open/whatsapp/onboard#token=synthetic", expires_at: new Date(Date.now() + 3600000).toISOString() } });
  });
  await page.goto("/e2e-ycloud/fixture.html?lang=en");
  await expect(page.getByRole("heading", { name: "WhatsApp", exact: true })).toBeVisible();
  await expect(page.getByTestId("ycloud-setup")).toHaveCount(0);
  releaseStatus();
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await start.click();
  await expect(page.getByRole("button", { name: "Loading...", exact: true })).toBeDisabled();
  await expect(page.getByRole("combobox")).toBeDisabled();
  releaseStart();
  await expect(page.getByRole("link", { name: "Continue connection" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(start).toBeEnabled();
  await expect(page.getByRole("link", { name: "Continue connection" })).toHaveCount(0);
  expect(posts).toEqual([{ action: "start", onboarding_type: "WHATSAPP_BUSINESS_PLATFORM", expected_phone_number: "" }, { action: "cancel" }]);
});
