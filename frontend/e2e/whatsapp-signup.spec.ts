import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

let pageErrors: string[];
test.beforeEach(({ page }) => { pageErrors = []; page.on("pageerror", (error) => pageErrors.push(error.message)); });
test.afterEach(() => { expect(pageErrors).toEqual([]); });

async function setup(page: Page, locale = "en") {
  let starts = 0;
  const completions: Record<string, unknown>[] = [];
  const startPayloads: Record<string, unknown>[] = [];
  await page.addInitScript((language) => {
    localStorage.setItem("ai_smb_language", language);
    const target = window as typeof window & { signupCallbacks: ((response: unknown) => void)[]; signupOptions: unknown[] };
    target.signupCallbacks = [];
    target.signupOptions = [];
    target.FB = { init() {}, login(callback, options) { target.signupCallbacks.push(callback); target.signupOptions.push(options); } };
  }, locale);
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    if (path.endsWith("/whatsapp-embedded-signup/start/")) {
      starts++;
      startPayloads.push(route.request().postDataJSON());
      return route.fulfill({ json: { app_configured: true, config_id_configured: true, app_id: "fake-app", config_id: "fake-config", state: `state-${starts}`, redirect_uri: "http://127.0.0.1:5173/callback", graph_api_version: "v27.0" } });
    }
    if (path.endsWith("/whatsapp-embedded-signup/complete/")) {
      completions.push(route.request().postDataJSON());
      return route.fulfill({ status: completions.length === 1 ? 400 : 200, json: completions.length === 1 ? { oauth: "Restart setup and try again." } : { ok: true, channel_id: 17 } });
    }
    return route.fulfill({ json: { phone_number_id_configured: false, access_token_configured: false } });
  });
  await page.goto("/e2e/fixtures/whatsapp-signup.html");
  await expect(page.getByRole("button", { name: /^(Connect|Подключить|Қосу)$/ })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(/Meta|YCloud/i);
  return { completions, startPayloads, starts: () => starts };
}

test("Business App uses coexistence callback without a phone ID or PIN and retains number on error", async ({ page }, testInfo) => {
  const { completions, startPayloads } = await setup(page);
  await page.getByRole("combobox").click();
  await page.getByRole("option", { name: /WhatsApp Business App/ }).click();
  const phone = page.getByLabel("WhatsApp Business app number", { exact: true });
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await expect(page.getByLabel(/PIN/)).toHaveCount(0);
  await phone.fill("87010000000");
  await expect(start).toBeDisabled();
  await phone.fill("+77010000000");
  await start.click();
  expect(startPayloads[0]).toMatchObject({ onboarding_mode: "coexistence", expected_phone: "+77010000000" });
  expect(await page.evaluate(() => (window as unknown as { signupOptions: unknown[] }).signupOptions[0])).toMatchObject({
    extras: { featureType: "whatsapp_business_app_onboarding", sessionInfoVersion: "3" },
  });
  await finish(page);
  await code(page, 0, "business-app-code");
  expect(completions).toHaveLength(0);
  await page.evaluate(() => window.dispatchEvent(new MessageEvent("message", { origin: "https://www.facebook.com", source: window,
    data: { type: "WA_EMBEDDED_SIGNUP", event: "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING", data: { waba_id: "456" } } })));
  await expect(start).toBeEnabled();
  expect(completions[0]).toMatchObject({ code: "business-app-code", phone_number_id: "", waba_id: "456" });
  expect(completions[0]).not.toHaveProperty("registration_pin");
  await expect(phone).toHaveValue("+77010000000");
  await page.screenshot({ path: testInfo.outputPath("coexistence-recovery.png"), fullPage: true });
});

for (const locale of ["ru", "kk", "en"]) for (const width of [390, 1440]) {
  test(`Business App layout ${locale} ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await setup(page, locale);
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: /WhatsApp Business App/ }).click();
    const phone = page.locator('input[type="tel"]');
    await phone.fill("+77010000000");
    await phone.press("Tab");
    await expect(page.getByRole("button", { name: /^(Connect|Подключить|Қосу)$/ })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const accessibility = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`coexistence-${locale}-${width}.png`), fullPage: true });
  });
}

async function code(page: Page, index: number, value?: string) {
  await page.waitForFunction((index) => typeof (window as unknown as { signupCallbacks: unknown[] }).signupCallbacks[index] === "function", index);
  await page.evaluate(({ index, value }) => {
    const callbacks = (window as unknown as { signupCallbacks: ((response: unknown) => void)[] }).signupCallbacks;
    callbacks[index]({ authResponse: value ? { code: value } : undefined });
  }, { index, value });
}

async function finish(page: Page, origin = "https://www.facebook.com", phone = "123") {
  await page.evaluate(({ origin, phone }) => window.dispatchEvent(new MessageEvent("message", {
    origin, source: window, data: JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "FINISH", data: { phone_number_id: phone, waba_id: "456" } }),
  })), { origin, phone });
}

test("complete only with matching attempt, account and PIN; error requires a fresh attempt", async ({ page }) => {
  const { completions } = await setup(page);
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await finish(page);
  const pin = page.getByLabel(/PIN/);
  await expect(start).toBeDisabled();
  await pin.fill("12345");
  await expect(start).toBeDisabled();
  await pin.fill("123456");
  await expect(pin).toHaveAttribute("type", "password");
  await start.click();
  await expect(start).toBeDisabled();
  await code(page, 0, "code-1");
  await finish(page, "https://evil.invalid");
  expect(completions).toHaveLength(0);
  await finish(page);
  await expect(start).toBeEnabled();
  await expect(pin).toHaveValue("123456");
  expect(completions).toHaveLength(1);
  expect(completions[0]).toMatchObject({ code: "code-1", state: "state-1", phone_number_id: "123", waba_id: "456", registration_pin: "123456" });
  await start.click();
  await code(page, 0, "stale-code");
  expect(completions).toHaveLength(1);
  // A new SDK popup has a new WindowProxy. The fixture uses an iframe to model it.
  await page.evaluate(() => {
    const frame = document.createElement("iframe"); document.body.appendChild(frame);
    window.dispatchEvent(new MessageEvent("message", { origin: "https://www.facebook.com", source: frame.contentWindow,
      data: { type: "WA_EMBEDDED_SIGNUP", event: "FINISH", data: { phone_number_id: "789", waba_id: "456" } } }));
    frame.remove();
  });
  expect(completions).toHaveLength(1);
  await code(page, 1, "code-2");
  await expect(pin).toHaveValue("");
  expect(completions[1]).toMatchObject({ code: "code-2", state: "state-2", phone_number_id: "789" });
});

test("cancel and denied login ignore late SDK callbacks and allow restart", async ({ page }) => {
  await setup(page);
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await page.getByLabel(/PIN/).fill("123456");
  await start.click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await code(page, 0, "late");
  await finish(page);
  await expect(page.getByLabel(/PIN/)).toHaveValue("123456");
  await start.click();
  await code(page, 1);
  await expect(start).toBeEnabled();
  await expect(page.getByLabel(/PIN/)).toHaveValue("123456");
});

for (const locale of ["ru", "kk", "en"]) for (const width of [390, 1440]) {
  test(`PIN and completion layout ${locale} ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await setup(page, locale);
    const pin = page.getByLabel(/PIN/);
    await pin.fill("123456");
    await expect(page.getByRole("button", { name: /^(Connect|Подключить|Қосу)$/ })).toBeEnabled();
    await pin.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toHaveAttribute("type", "button");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const accessibility = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`${locale}-${width}.png`), fullPage: true, animations: "disabled" });
  });
}

test("SDK load failure can be retried without a stale script", async ({ page }) => {
  await setup(page);
  await page.evaluate(() => { delete window.FB; });
  await page.route("https://connect.facebook.net/**", (route) => route.abort());
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await page.getByLabel(/PIN/).fill("123456");
  await start.click();
  await expect(page.getByText(/connection needs attention|could not|try again/i).first()).toBeVisible();
  await expect(start).toBeEnabled();
  expect(await page.locator('script[src*="connect.facebook.net"]').count()).toBe(0);
  await page.evaluate(() => {
    window.FB = { init() {}, login(callback) { (window as unknown as { signupCallbacks: unknown[] }).signupCallbacks.push(callback); } };
  });
  await start.click();
  await code(page, 0, "recovered");
  await finish(page);
  await expect(page.getByLabel(/PIN/)).toBeVisible();
});

test("read-only manager cannot start signup", async ({ page }) => {
  const state = await setup(page);
  await page.goto("/e2e/fixtures/whatsapp-signup.html?readonly");
  await expect(page.getByRole("button", { name: "Connect", exact: true })).toBeDisabled();
  expect(state.starts()).toBe(0);
});

test("connected channel can edit setup then cancel without changing its connection", async ({ page }) => {
  const state = await setup(page);
  await page.route("**/whatsapp-status/", route => route.fulfill({ json: {
    phone_number_id_configured: true, access_token_configured: true,
    coexistence_sync: { state: "complete", progress: 100, pending_batches: 0, error_code: "" },
  } }));
  await page.reload();
  await expect(page.getByText(/Received history batches/)).toBeVisible();
  await page.getByRole("button", { name: "Change connection", exact: true }).click();
  await expect(page.getByLabel(/PIN/)).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("button", { name: "Change connection", exact: true })).toBeVisible();
  expect(state.starts()).toBe(0);
});

test("WABA-only and same-origin state mismatch never enable completion", async ({ page }) => {
  const { completions } = await setup(page);
  await page.getByLabel(/PIN/).fill("123456");
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await code(page, 0, "code");
  await page.evaluate(() => {
    window.dispatchEvent(new MessageEvent("message", { origin: "https://www.facebook.com", source: window,
      data: { type: "WA_EMBEDDED_SIGNUP", event: "FINISH_ONLY_WABA", data: { waba_id: "456" } } }));
    window.dispatchEvent(new MessageEvent("message", { origin: location.origin, source: window,
      data: { type: "zani.whatsapp.embedded_signup_callback", state: "foreign", phone_number_id: "123", waba_id: "456" } }));
  });
  expect(completions).toHaveLength(0);
  await expect(page.getByRole("button", { name: "Connect", exact: true })).toBeDisabled();
});

test("incomplete callback expires without replaying its code", async ({ page }) => {
  const { completions } = await setup(page);
  await page.clock.install();
  await page.getByLabel(/PIN/).fill("123456");
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await start.click();
  await code(page, 0, "expired-code");
  await page.clock.fastForward(21000);
  await expect(start).toBeEnabled();
  await finish(page);
  expect(completions).toHaveLength(0);
  await expect(page.getByLabel(/PIN/)).toHaveValue("123456");
});

test("registration stays busy and duplicate callbacks submit only once", async ({ page }, testInfo) => {
  await setup(page);
  let calls = 0;
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/whatsapp-embedded-signup/complete/", async route => {
    calls++;
    await pending;
    await route.fulfill({ json: { ok: true, channel_id: 17 } });
  });
  const pin = page.getByLabel(/PIN/);
  const start = page.getByRole("button", { name: "Connect", exact: true });
  await pin.fill("123456");
  await start.click();
  await finish(page);
  await code(page, 0, "one-use-code");
  await expect.poll(() => calls).toBe(1);
  await expect(page.getByRole("button", { name: "Loading...", exact: true })).toBeDisabled();
  await expect(pin).toBeDisabled();
  await page.screenshot({ path: testInfo.outputPath("registration-busy.png"), fullPage: true });
  await finish(page);
  await code(page, 0, "duplicate-code");
  expect(calls).toBe(1);
  release();
  await expect(pin).toHaveValue("");
  expect(calls).toBe(1);
});

for (const width of [390, 1440]) test(`setup dialog closes and returns focus ${width}`, async ({ page }, testInfo) => {
  await page.setViewportSize({ width, height: 900 });
  await setup(page, "kk");
  await page.goto("/e2e/fixtures/whatsapp-signup.html?dialog");
  const opener = page.getByRole("button", { name: "Open WhatsApp" });
  await opener.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.getByLabel(/PIN/).fill("123456");
  await expect(dialog.getByRole("button", { name: "Қосу", exact: true })).toBeEnabled();
  await page.getByLabel(/PIN/).press("Tab");
  await expect(dialog.getByRole("button", { name: "Қосу", exact: true })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath(`dialog-${width}.png`), fullPage: true });
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
  await opener.press("Enter");
  await expect(page.getByLabel(/PIN/)).toHaveValue("");
});
