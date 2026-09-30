import { expect, test, type Page } from "@playwright/test";
import type { CurrentUser, Notification } from "../src/types";
import { resetAccountPreferences } from "./support/account-preferences";

test.afterEach(async ({ request }) => resetAccountPreferences(request));

async function login(page: Page, email = process.env.E2E_OWNER_EMAIL || "business_owner@example.com") {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
}

test("start page persists, normal entry uses it and role limits available choices", async ({ page, context }, testInfo) => {
  test.setTimeout(60_000);
  await login(page);
  await page.goto("/app/account");
  const card = page.locator("#interface");
  await card.getByRole("combobox", { name: /Стартовая страница/ }).click();
  await page.getByRole("option", { name: "Задачи", exact: true }).click();
  const saved = page.waitForResponse(response => response.url().endsWith("/api/auth/me/") && response.request().method() === "PATCH");
  await card.locator('button[type="submit"]').click();
  expect((await saved).request().postDataJSON()).toEqual({ preferences: { language: "ru", start_page: "tasks" } });
  await expect(card.getByRole("status")).toHaveText("Настройки сохранены.");
  await page.goto("/app");
  await expect(page).toHaveURL(/\/app\/tasks$/);
  await page.goto("/app/calendar");
  await expect(page).toHaveURL(/\/app\/calendar$/);
  // Wait for the authenticated page, not just the browser URL. An immediate
  // second document navigation can abort refresh-token rotation mid-response.
  await page.getByTestId("header-account-link").click();
  await expect(card).toBeVisible();
  const loggedOut = page.waitForResponse(response => response.url().includes("/api/auth/logout/") && response.request().method() === "POST");
  await page.getByTestId("merchant-logout").click();
  await loggedOut;
  await expect(page).toHaveURL(/\/login/);
  const entry = await context.newPage();
  await login(entry);
  await expect(entry).toHaveURL(/\/app\/tasks$/);
  await entry.close();
  await page.goto("/app/account");
  await card.getByRole("combobox", { name: /Стартовая страница/ }).click();
  await page.getByRole("option", { name: "Главная", exact: true }).click();
  await card.locator('button[type="submit"]').click();
  await expect(card.locator('button[type="submit"]')).toBeDisabled();

  await page.route("**/api/auth/me/", async route => {
    const response = await route.fetch();
    const current = await response.json() as CurrentUser;
    const businessId = current.businesses[0].id;
    current.preferences!.start_page = "calendar";
    current.role = "staff";
    current.memberships = [{ business: businessId, role: "specialist", business_role: null, business_role_name: "", is_active: true }];
    current.effective_permissions = { [String(businessId)]: [{ resource: "tasks", action: "view", scope: "own" }] };
    await route.fulfill({ response, json: current });
  });
  await page.reload();
  await card.getByRole("combobox", { name: /Стартовая страница/ }).click();
  await expect(page.getByRole("option")).toHaveText(["Главная", "Задачи"]);
  await page.keyboard.press("Escape");
  const access = page.getByTestId("account-access-summary");
  await access.locator("summary").click();
  await expect(access.getByText("Задачи", { exact: true })).toBeVisible();
  await expect(access.getByText("Свои записи", { exact: true })).toBeVisible();
  await expect(access.getByText("Календарь и записи", { exact: true })).toHaveCount(0);
  await expect(access.getByRole("button")).toHaveCount(0);
  await page.screenshot({ path: `../output/account-interface-access-${testInfo.project.name}.png`, fullPage: true });
  await page.goto("/app");
  await expect(page).toHaveURL(/\/app\/dashboard$/);
});

test("notification chime is optional, previews and sounds once for new arrivals", async ({ page, context }) => {
  await context.addInitScript(() => {
    const state = window as typeof window & { soundStarts: number };
    state.soundStarts = 0;
    class AudioContextStub {
      state = "running";
      currentTime = 0;
      destination = {};
      async resume() { this.state = "running"; }
      createOscillator() {
        return { type: "sine", frequency: { value: 0 }, connect() {}, disconnect() {},
          start() { state.soundStarts += 1; }, stop() {}, onended: null };
      }
      createGain() {
        return { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} }, connect() {}, disconnect() {} };
      }
    }
    Object.defineProperty(window, "AudioContext", { value: AudioContextStub, configurable: true });
  });
  let items: Partial<Notification>[] = [{ id: 7001, send_at: "2026-09-30T10:00:00Z", read_at: null }];
  await context.route(/\/api\/notifications\/\?/, route => route.fulfill({ json: items }));
  await login(page);
  await page.goto("/app/account");
  await page.clock.install();
  const card = page.locator("#interface");
  const toggle = card.getByRole("switch", { name: "Звук уведомлений" });
  const starts = () => page.evaluate(() => (window as typeof window & { soundStarts: number }).soundStarts);
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await card.getByRole("button", { name: "Прослушать" }).click();
  await expect.poll(starts).toBe(2);
  const baseline = page.waitForResponse(response => /\/api\/notifications\/\?/.test(response.url()));
  await toggle.click();
  await baseline;
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  expect(await starts()).toBe(2);
  items = [{ id: 7002, send_at: "2026-09-30T10:01:00Z", read_at: null }, ...items];
  await page.clock.fastForward(61_000);
  await expect.poll(starts).toBe(4);
  await page.clock.fastForward(61_000);
  expect(await starts()).toBe(4);
  items[1].read_at = "2026-09-30T10:02:00Z";
  await page.clock.fastForward(61_000);
  items[1].read_at = null;
  await page.clock.fastForward(61_000);
  expect(await starts()).toBe(4);
  await toggle.click();
  items = [{ id: 7003, send_at: "2026-09-30T10:03:00Z", read_at: null }, ...items];
  await page.clock.fastForward(61_000);
  expect(await starts()).toBe(4);
  const unmute = page.waitForResponse(response => /\/api\/notifications\/\?/.test(response.url()));
  await toggle.click();
  await unmute;
  await page.clock.fastForward(61_000);
  expect(await starts()).toBe(4);
  const peer = await context.newPage();
  const peerBaseline = peer.waitForResponse(response => /\/api\/notifications\/\?/.test(response.url()));
  await peer.goto("/app/account");
  await peerBaseline;
  await peer.locator("#interface").getByRole("heading").click();
  await peer.clock.install();
  items = [{ id: 7004, send_at: "2026-09-30T10:04:00Z", read_at: null }, ...items];
  await Promise.all([page.clock.fastForward(61_000), peer.clock.fastForward(61_000)]);
  await expect.poll(async () => await starts() + await peer.evaluate(() => (window as typeof window & { soundStarts: number }).soundStarts)).toBe(6);
  await peer.close();
  await page.reload();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  expect(await starts()).toBe(0);
  const loggedOut = page.waitForResponse(response => response.url().includes("/api/auth/logout/") && response.request().method() === "POST");
  await page.getByTestId("merchant-logout").click();
  await loggedOut;
  await login(page, "business_operator@example.com");
  await page.goto("/app/account");
  await expect(toggle).toHaveAttribute("aria-checked", "false");
});

test("notification preview runs through native browser audio", async ({ page }) => {
  await page.addInitScript(() => {
    const state = window as typeof window & { nativeAudioState?: string; nativeAudioEnded: number };
    state.nativeAudioEnded = 0;
    const NativeAudioContext = window.AudioContext;
    class ObservedAudioContext extends NativeAudioContext {
      createOscillator() {
        state.nativeAudioState = this.state;
        const oscillator = super.createOscillator();
        oscillator.addEventListener("ended", () => { state.nativeAudioEnded += 1; });
        return oscillator;
      }
    }
    Object.defineProperty(window, "AudioContext", { value: ObservedAudioContext });
  });
  await login(page);
  await page.goto("/app/account");
  await page.locator("#interface").getByRole("button", { name: "Прослушать" }).click();
  await expect.poll(() => page.evaluate(() => (window as typeof window & { nativeAudioEnded: number }).nativeAudioEnded)).toBe(2);
  expect(await page.evaluate(() => (window as typeof window & { nativeAudioState?: string }).nativeAudioState)).toBe("running");
  await expect(page.locator("#interface").getByRole("alert")).toHaveCount(0);
});

test("browser audio failure stays recoverable and leaves sound disabled", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "AudioContext", { value: class { constructor() { throw new Error("Audio blocked"); } } });
  });
  await login(page);
  await page.goto("/app/account");
  const card = page.locator("#interface");
  await card.getByRole("switch", { name: "Звук уведомлений" }).click();
  await expect(card.getByRole("alert")).toContainText("Не удалось включить звук");
  await expect(card.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  await expect(card.getByRole("combobox", { name: /Стартовая страница/ })).toBeEnabled();
});
