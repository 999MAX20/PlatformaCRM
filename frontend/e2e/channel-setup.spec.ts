import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(({ page }) => {
  page.on("pageerror", error => { throw error; });
});

async function setup(page: Page, locale = "en", readonly = false, initial = false) {
  const channels = ["website", "telegram", "whatsapp", "instagram"].map((channel, i) => ({ id: i + 1, bot: 9, channel, status: initial ? "draft" : "paused", config_json: {}, public_token: "synthetic-widget-token" }));
  let tokenConfigured = !initial, verified = !initial, webhook = !initial, failStatus = false, failPatch = false, failSave = false, instagramConnected = false;
  const writes: { path: string; data: Record<string, unknown> }[] = [];
  await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), locale);
  await page.route(url => url.pathname.startsWith("/api/"), async route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    if (req.method() !== "GET") writes.push({ path, data: req.postDataJSON() });
    if (path === "/api/bot-channels/") return route.fulfill({ json: channels });
    if (req.method() === "PATCH") {
      if (failPatch) return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
      const channel = channels.find(c => path === `/api/bot-channels/${c.id}/`)!;
      Object.assign(channel, req.postDataJSON()); return route.fulfill({ json: channel });
    }
    if (path.endsWith("telegram-status/")) return route.fulfill({ status: failStatus ? 503 : 200, json: failStatus ? { detail: "Unavailable" } : { token_configured: tokenConfigured, token_verified: verified, webhook_configured: webhook, webhook_url: "https://example.invalid/hook" } });
    if (path.endsWith("telegram-config/")) {
      if (failSave) return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
      tokenConfigured = true; verified = false; webhook = false; channels[1].status = "draft"; return route.fulfill({ json: { ok: true } });
    }
    if (path.endsWith("telegram-test-connection/")) { verified = true; return route.fulfill({ json: { ok: true } }); }
    if (path.endsWith("set-telegram-webhook/")) { webhook = true; channels[1].status = "active"; return route.fulfill({ json: { ok: true } }); }
    if (path.endsWith("whatsapp-status/")) return route.fulfill({ json: { access_token_configured: false } });
    if (path.endsWith("instagram-status/")) return route.fulfill({ json: { access_token_configured: instagramConnected, instagram_user_id_configured: instagramConnected } });
    if (path.endsWith("instagram-oauth/start/")) return route.fulfill({ json: { app_configured: true, state: "test-state", redirect_uri: "https://example.invalid/callback", authorization_url: "https://example.invalid/authorize" } });
    if (path.endsWith("instagram-oauth/complete/")) {
      if (failSave) return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
      instagramConnected = true; channels[3].status = "active"; return route.fulfill({ json: { ok: true } });
    }
    if (path.endsWith("whatsapp-config/")) return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
    if (path.includes("ycloud")) return route.fulfill({ json: { available: false, status: "not_connected", channel_status: "draft" } });
    throw new Error(`Unexpected API request: ${req.method()} ${path}`);
  });
  await page.goto(`/e2e/fixtures/channel-setup.html${readonly ? "?readonly" : ""}`);
  await expect(page.getByRole("button", { name: "Configure", exact: true })).toHaveCount(locale === "en" ? 4 : 0);
  return { writes, channels, failStatus: (value: boolean) => { failStatus = value; }, failPatch: (value: boolean) => { failPatch = value; }, failSave: (value: boolean) => { failSave = value; } };
}
const open = (page: Page, name: string) => page.locator("article").filter({ has: page.getByRole("heading", { name, exact: true }) }).getByRole("button", { name: "Configure", exact: true }).click();

test("Telegram paused status, replacement cancellation, validation and complete reconnect", async ({ page }) => {
  const state = await setup(page);
  await open(page, "Telegram");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Paused", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Replace bot token" }).click();
  const token = dialog.getByLabel("Bot key", { exact: true });
  await token.fill("synthetic-crm-password");
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Save key", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  expect(state.writes).toEqual([]);
  await dialog.getByRole("button", { name: "Replace bot token" }).click();
  await token.fill("123456789:synthetic_bot_secret");
  await dialog.getByRole("button", { name: "Save key", exact: true }).click();
  await expect(token).toHaveValue("");
  await dialog.getByRole("button", { name: "Check connection", exact: true }).click();
  await dialog.getByRole("button", { name: "Connect incoming", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Replace bot token" })).toBeVisible();
  expect(state.writes.map(w => w.path)).toEqual(["/api/bot-channels/2/telegram-config/", "/api/bot-channels/2/telegram-test-connection/", "/api/bot-channels/2/set-telegram-webhook/"]);
});

test("website copy, failed toggle recovery and persisted active state", async ({ page }) => {
  const state = await setup(page);
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await open(page, "Website");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/local environment/)).toBeVisible();
  await dialog.getByRole("button", { name: "Copy install code" }).click();
  await expect(dialog.getByText("Code copied", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain("synthetic-widget-token");
  state.failPatch(true); await dialog.getByRole("switch").click();
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  state.failPatch(false); await dialog.getByRole("switch").click();
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  await expect(dialog.getByText(/channel is on/i)).toBeVisible();
});

test("status failure retries; WhatsApp offers one provider-neutral connection action", async ({ page }) => {
  const state = await setup(page); state.failStatus(true);
  await open(page, "Telegram");
  await expect(page.getByRole("dialog").getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  state.failStatus(false); await page.getByRole("dialog").getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("button", { name: "Replace bot token" })).toBeVisible();
  await page.keyboard.press("Escape");
  await open(page, "WhatsApp");
  await expect(page.getByRole("dialog").getByRole("button", { name: "Connect", exact: true })).toHaveCount(1);
  await expect(page.getByRole("dialog")).not.toContainText(/Meta|YCloud|Manual setup/i);
  await expect(page.getByRole("dialog").locator("input")).toHaveCount(0);
  expect(state.writes).toEqual([]);
});

test("read-only channels cannot mutate", async ({ page }) => {
  const state = await setup(page, "en", true);
  for (const button of await page.getByRole("button", { name: "Configure", exact: true }).all()) await expect(button).toBeDisabled();
  expect(state.writes).toEqual([]);
});

test("new Telegram key is masked, revealable and retained after failure; connection uses existing endpoints", async ({ page }) => {
  const state = await setup(page, "en", false, true);
  await open(page, "Telegram");
  const dialog = page.getByRole("dialog"), token = dialog.getByLabel("Bot key", { exact: true });
  const connect = dialog.getByRole("button", { name: "Connect", exact: true });
  await expect(token).toHaveValue("");
  await expect(connect).toBeDisabled();
  await token.fill("123456789:synthetic_bot_secret");
  await expect(token).toHaveAttribute("type", "password");
  await dialog.getByRole("button", { name: "Show key", exact: true }).click();
  await expect(token).toHaveAttribute("type", "text");
  await dialog.getByRole("button", { name: "Hide key", exact: true }).click();
  await expect(token).toHaveAttribute("type", "password");
  state.failSave(true); await connect.click();
  await expect(dialog.getByRole("alert").first()).toBeVisible();
  await expect(token).toHaveValue("123456789:synthetic_bot_secret");
  state.failSave(false); await connect.click();
  await expect(token).toHaveValue("");
  await dialog.getByRole("button", { name: "Check connection", exact: true }).click();
  await dialog.getByRole("button", { name: "Connect incoming", exact: true }).click();
  await expect(dialog.getByText("Connected", { exact: true })).toBeVisible();
  expect(state.writes.map(w => w.path)).toEqual(["/api/bot-channels/2/telegram-config/", "/api/bot-channels/2/telegram-config/", "/api/bot-channels/2/telegram-test-connection/", "/api/bot-channels/2/set-telegram-webhook/"]);
});

test("Instagram selection, callback, failed completion recovery and connected controls", async ({ page }) => {
  const state = await setup(page, "en", false, true);
  await page.evaluate(() => { window.open = () => null; });
  await open(page, "Instagram");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Instagram account", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Connect", exact: true }).click();
  await expect.poll(() => state.writes.length).toBe(1);
  await page.evaluate(() => window.dispatchEvent(new MessageEvent("message", { origin: location.origin, data: { type: "zani.instagram.oauth_callback", code: "test-code", state: "test-state" } })));
  const complete = dialog.getByRole("button", { name: "Complete connection", exact: true });
  state.failSave(true); await complete.click();
  await expect(dialog.getByRole("alert").first()).toBeVisible();
  await expect(complete).toBeEnabled();
  state.failSave(false); await complete.click();
  await expect(dialog.getByText("Connected", { exact: true })).toBeVisible();
  await expect(complete).toHaveCount(0);
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  expect(state.writes.at(-1)?.data).toMatchObject({ business: 7, code: "test-code", state: "test-state" });
  await dialog.getByRole("switch").click();
  await expect(dialog.getByText("Paused", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Manual setup", exact: true }).click();
  await expect(dialog.locator('input[type="password"]')).toHaveValue("");
  await dialog.getByRole("button", { name: "Hide manual setup", exact: true }).click();
  await dialog.getByRole("link", { name: "Open messages" }).click();
  await expect(page).toHaveURL(/\/app\/conversations\?channel=instagram$/);
});

test("website first connection and clipboard denial recover without changing the code", async ({ page }) => {
  const state = await setup(page, "en", false, true);
  await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: () => Promise.reject(new Error("Denied")) } }));
  await open(page, "Website");
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Copy install code" }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.locator("pre")).toContainText("synthetic-widget-token");
  state.failPatch(true);
  await dialog.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Connect", exact: true })).toBeEnabled();
  state.failPatch(false);
  await dialog.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(dialog.getByText("Connected", { exact: true })).toBeVisible();
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  await expect(dialog.getByRole("button", { name: "Connect", exact: true })).toHaveCount(0);
  expect(state.writes).toHaveLength(2);
});

test("configured WhatsApp preserves its connection and pause controls", async ({ page }) => {
  const state = await setup(page);
  state.channels[2].status = "active";
  await page.route(url => url.pathname.endsWith("whatsapp-status/"), route => route.fulfill({ json: { access_token_configured: true, phone_number_id_configured: true } }));
  await page.reload();
  await open(page, "WhatsApp");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Connect", exact: true })).toHaveCount(0);
  await expect(dialog.locator("input")).toHaveCount(0);
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  await dialog.getByRole("switch").click();
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  await dialog.getByRole("switch").click();
  await expect(dialog.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  expect(state.writes.map(write => write.data)).toEqual([{ status: "paused" }, { status: "active" }]);
});

test("channel dialogs reflow at 200 percent text size and keep actions reachable", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setup(page, "kk", false, true);
  await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
  for (const index of [0, 1, 2, 3]) {
    const trigger = page.locator("article").nth(index).locator("button").first();
    await trigger.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    const action = dialog.getByRole("button", { name: "Қосу", exact: true });
    await action.scrollIntoViewIfNeeded();
    await expect(action).toBeInViewport();
    await page.screenshot({ path: testInfo.outputPath(`large-text-${index}.png`) });
    await page.keyboard.press("Escape");
    await expect(trigger).toBeFocused();
  }
});

for (const locale of ["ru", "kk", "en"]) {
  for (const width of [320, 768, 1440]) {
    test(`channel dialogs keyboard, accessibility and layout ${locale} ${width}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      await setup(page, locale, false, true);
      await expect(page.locator("article")).toHaveCount(4);
      for (const index of [0, 1, 2, 3]) {
        const trigger = page.locator("article").nth(index).locator("button").first();
        await trigger.focus();
        await page.keyboard.press("Enter");
        const dialog = page.getByRole("dialog");
        await expect(dialog).toBeVisible();
        await expect(dialog.getByRole("heading", { name: { ru: "Как подключить", kk: "Қалай қосуға болады", en: "How to connect" }[locale], exact: true })).toBeVisible();
        await expect(dialog.getByRole("heading", { level: 2 })).toHaveCount(1);
        expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
        const accessibility = await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze();
        expect(accessibility.violations).toEqual([]);
        await page.screenshot({ path: testInfo.outputPath(`channel-${index}-${locale}-${width}.png`) });
        await page.keyboard.press("Escape");
        await expect(dialog).toHaveCount(0);
        await expect(trigger).toBeFocused();
      }
    });
  }
}
