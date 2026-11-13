import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { InboxConversation } from "../src/api/inbox";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.use({ actionTimeout: 12_000 });

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
});

const visibleLoaders = (page: Page) => page.locator(".platforma-loading").filter({ visible: true });
function hold() {
  let release!: () => void;
  const promise = new Promise<void>(resolve => { release = resolve; });
  return { promise, release };
}

test("Inbox waits once for its initial visible data and does not wait for channel readiness", async ({ page }, info) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const messages = hold(), context = hold(), channels = hold();
  let contextStarted = false;
  await page.route(`**/api/inbox/conversations/${conversation.id}/messages/**`, async route => { await messages.promise; await route.continue(); });
  await page.route(`**/api/inbox/conversations/${conversation.id}/context/`, async route => { contextStarted = true; await context.promise; await route.continue(); });
  await page.route("**/api/business-connectors/**", async route => { await channels.promise; await route.continue(); });
  try {
    await page.goto(`/app/conversations/${conversation.id}`);
    await expect.poll(() => contextStarted).toBe(true);
    await expect(visibleLoaders(page)).toHaveCount(1);
    await expect(visibleLoaders(page).locator(".platforma-loading__content")).toHaveCSS("opacity", "1");
    await expect(page.getByTestId("inbox-workspace-ready")).toBeHidden();
    await page.screenshot({ animations: "disabled", path: info.outputPath("inbox-initial.png") });
    messages.release();
    await expect(page.getByTestId("inbox-workspace-ready")).toBeHidden();
    context.release();
    await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
    await expect(visibleLoaders(page)).toHaveCount(0);
    const list = page.getByTestId("inbox-conversation-list");
    const before = await list.boundingBox();
    channels.release();
    await expect(list).toHaveAttribute("aria-busy", "false");
    expect((await list.boundingBox())!.y).toBe(before!.y);
    await page.screenshot({ animations: "disabled", path: info.outputPath("inbox-ready.png") });
  } finally { messages.release(); context.release(); channels.release(); }
});

const pageCases = [
  { name: "dashboard", url: "/app/dashboard", api: "**/api/analytics/owner-dashboard/**", ready: '[data-testid="dashboard-workspace-ready"]' },
  { name: "calendar", url: "/app/calendar", api: "**/api/working-hours/**", ready: '[data-testid="calendar-workspace-ready"]' },
  { name: "account", url: "/app/account", api: "**/api/auth/sessions/**", ready: "[data-account-page]" },
  { name: "team settings", url: "/app/settings#team-access", api: "**/api/team/members/**", ready: '[data-testid="settings-workspace-ready"]' },
  { name: "tasks", url: "/app/tasks", api: "**/api/tasks/summary/**", ready: '[data-testid="tasks-workspace-ready"]' },
  { name: "records", url: "/app/appointments", api: "**/api/appointments/workspace/**", ready: '[data-testid="records-workspace"]' },
  { name: "clients", url: "/app/clients", api: "**/api/clients/**", ready: '[data-workspace-content]' },
  { name: "branches", url: "/app/business/branches", api: "**/api/management/**", ready: '[data-workspace-content]' },
  { name: "notifications", url: "/app/notifications", api: "**/api/notifications/**", ready: '[data-testid="notifications-page"]' },
  { name: "voice history", url: "/app/voice/history", api: "**/api/ai/conversations/**", ready: '[data-testid="voice-history"]' },
  { name: "import", url: "/app/integrations/import", api: "**/api/import-workspaces/**", ready: '[data-workspace-content]' },
];

for (const item of pageCases) test(`${item.name} shows one initial loader then usable content`, async ({ page }, info) => {
  await crmSession(page);
  const waiting = hold();
  let started = false;
  await page.route(item.api, async route => { started = true; await waiting.promise; await route.continue(); });
  try {
    await page.goto(item.url);
    await expect.poll(() => started).toBe(true);
    await expect(visibleLoaders(page)).toHaveCount(1);
    await expect(page.getByTestId("page-loading").filter({ visible: true })).toHaveCount(1);
    await page.screenshot({ animations: "disabled", path: info.outputPath("initial.png") });
    waiting.release();
    await expect(visibleLoaders(page)).toHaveCount(0);
    await expect(page.locator(item.ready)).toBeVisible();
    await page.screenshot({ animations: "disabled", path: info.outputPath("ready.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  } finally { waiting.release(); }
});

test("hidden settings queries cannot delay the active section", async ({ page }, info) => {
  await crmSession(page);
  const waiting = hold();
  await page.route("**/api/team/members/**", async route => { await waiting.promise; await route.continue(); });
  try {
    await page.goto("/app/settings#business-profile");
    await expect(page.getByTestId("settings-workspace-ready")).toBeVisible();
    await expect(visibleLoaders(page)).toHaveCount(0);
    await page.screenshot({ animations: "disabled", path: info.outputPath("settings-hidden-query.png") });
  } finally { waiting.release(); }
});

test("empty Inbox finishes initial loading", async ({ page }, info) => {
  await crmSession(page);
  await page.route(/\/api\/inbox\/conversations\/(?:\?|$)/, route => route.fulfill({ json: { count: 0, results: [], next: null, previous: null } }));
  await page.goto("/app/conversations");
  await expect(page.getByText(ru["conversations.emptyTitle"], { exact: true })).toBeVisible();
  await expect(visibleLoaders(page)).toHaveCount(0);
  await page.screenshot({ animations: "disabled", path: info.outputPath("empty.png") });
});

test("initial loading fits narrow enlarged text and keeps hidden controls out of focus", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 320, height: 700 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const waiting = hold();
  await page.route(`**/api/inbox/conversations/${conversation.id}/messages/**`, async route => {
    await waiting.promise;
    await route.continue();
  });
  try {
    await page.goto(`/app/conversations/${conversation.id}`);
    await expect(visibleLoaders(page)).toHaveCount(1);
    await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
    const content = visibleLoaders(page).locator(".platforma-loading__content");
    await expect(content).toContainText(ru["common.loadingData"]);
    const box = await content.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(320);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => Boolean(document.activeElement?.closest("[hidden], [inert]")))).toBe(false);
    await page.screenshot({ animations: "disabled", path: info.outputPath("loading-320-text-200.png") });
    await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
    waiting.release();
    await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
    expect(errors).toEqual([]);
  } finally { waiting.release(); }
});

test("route navigation keeps the shell and cached return never blanks the page", async ({ page }, info) => {
  await crmSession(page);
  await page.goto("/app/conversations");
  await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
  const waiting = hold();
  await page.route("**/api/tasks/summary/**", async route => { await waiting.promise; await route.continue(); });
  try {
    await page.locator('nav a[href="/app/tasks"]').first().click();
    await expect(page.getByTestId("page-loading").filter({ visible: true })).toHaveCount(1);
    await expect(page.getByTestId("header-account-link")).toBeVisible();
    await page.screenshot({ animations: "disabled", path: info.outputPath("navigation-loading.png") });
    waiting.release();
    await expect(page.getByTestId("tasks-workspace-ready")).toBeVisible();
    await page.locator('nav a[href="/app/conversations"]').first().click();
    await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
    await expect(visibleLoaders(page)).toHaveCount(0);
  } finally { waiting.release(); }
});

test("platform details waits for its visible section", async ({ page }, info) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("platform_admin@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("overview-attention")).toBeVisible();
  await page.goto("/platform/merchants");
  const link = page.getByTestId("platform-clinic-row").first().getByRole("link");
  const href = await link.getAttribute("href");
  expect(href).toBeTruthy();
  const waiting = hold();
  let started = false;
  await page.route("**/api/platform/merchants/*/details/", async route => { started = true; await waiting.promise; await route.continue(); });
  try {
    await page.goto(`${href!.split("?")[0]}?section=details`);
    await expect.poll(() => started).toBe(true);
    await expect(visibleLoaders(page)).toHaveCount(1);
    await page.screenshot({ animations: "disabled", path: info.outputPath("platform-initial.png") });
    waiting.release();
    await expect(page.getByTestId("platform-clinic-detail")).toBeVisible();
    await expect(visibleLoaders(page)).toHaveCount(0);
    await page.screenshot({ animations: "disabled", path: info.outputPath("platform-ready.png") });
  } finally { waiting.release(); }
});

test("Inbox initial failure exits loading and retry restores the page", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const pattern = `**/api/inbox/conversations/${conversation.id}/messages/**`;
  await page.route(pattern, route => route.fulfill({ status: 503, json: { detail: "Temporary fixture failure" } }));
  await page.goto(`/app/conversations/${conversation.id}`);
  await expect(page.getByTestId("page-loading").filter({ visible: true })).toHaveCount(0);
  const retry = page.getByRole("button", { name: ru["common.retry"], exact: true });
  await expect(retry).toBeVisible();
  await page.unroute(pattern);
  await retry.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
});

test("Inbox polling failure preserves the draft; access denial hides the data", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  await page.goto(`/app/conversations/${conversation.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await composer.fill("Retain my draft after polling");
  const pattern = `**/api/inbox/conversations/${conversation.id}/messages/**`;
  await page.route(pattern, route => route.fulfill({ status: 503, json: { detail: "Temporary fixture failure" } }));
  await expect(page.getByTestId("inbox-refresh-error")).toBeVisible({ timeout: 25_000 });
  await expect(composer).toHaveValue("Retain my draft after polling");
  await expect(visibleLoaders(page)).toHaveCount(0);
  await page.unroute(pattern);
  await page.getByTestId("inbox-refresh-error").getByRole("button").click();
  await expect(page.getByTestId("inbox-refresh-error")).toHaveCount(0);
  await expect(composer).toHaveValue("Retain my draft after polling");
  await page.route(pattern, route => route.fulfill({ status: 403, json: { detail: "Access revoked", code: "permission_denied" } }));
  await expect(page.getByTestId("inbox-error-state")).toBeVisible({ timeout: 25_000 });
  await expect(composer).toHaveCount(0);
  await expect(visibleLoaders(page)).toHaveCount(0);
});

for (const [language, width, copy] of [["ru", 390, ru], ["kk", 768, kk], ["en", 1440, en]] as const) {
  test(`Inbox localized loading and inspector keyboard recovery ${language} ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    const session = await crmSession(page);
    const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
    const waiting = hold();
    let started = false;
    await page.route(`**/api/inbox/conversations/${conversation.id}/messages/**`, async route => { started = true; await waiting.promise; await route.continue(); });
    try {
      await page.goto(`/app/conversations/${conversation.id}`);
      await expect.poll(() => started).toBe(true);
      await expect(visibleLoaders(page)).toHaveCount(1);
      await expect(visibleLoaders(page)).toContainText(copy["common.loadingData"]);
      await expect(visibleLoaders(page).locator(".platforma-loading__ring")).toHaveCSS("animation-name", "none");
      await page.screenshot({ animations: "disabled", path: info.outputPath("initial.png") });
      waiting.release();
      await expect(page.getByTestId("inbox-action-composer")).toBeVisible();
      await expect(visibleLoaders(page)).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ animations: "disabled", path: info.outputPath("ready.png") });
      const trigger = page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true });
      if (width < 1440) {
        await trigger.focus(); await page.keyboard.press("Enter");
        await expect(page.getByTestId("inbox-customer-context").filter({ visible: true })).toBeVisible();
        await page.screenshot({ animations: "disabled", path: info.outputPath("inspector.png") });
        await page.keyboard.press("Escape");
        await expect(trigger).toBeFocused();
      }
    } finally { waiting.release(); }
  });
}

test("Inbox selection keeps its list and draft, with one local loading status", async ({ page }, info) => {
  const session = await crmSession(page);
  const first = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const second = { ...first, id: first.id + 100000, client_name: "Loading switch fixture" };
  const secondContext = await session.read(`inbox/conversations/${first.id}/context`);
  await page.route(/\/api\/inbox\/conversations\/(?:\?|$)/, route => route.fulfill({ json: { count: 2, next: null, previous: null, results: [first, second] } }));
  await page.route(`**/api/inbox/conversations/${second.id}/`, route => route.fulfill({ json: second }));
  await page.route(`**/api/inbox/conversations/${second.id}/mark-read/`, route => route.fulfill({ json: second }));
  expect(second.id).not.toBe(first.id);
  await page.goto(`/app/conversations/${first.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await expect(composer).toBeVisible();
  await composer.fill("Keep this unsent draft");
  const waiting = hold();
  await page.route(`**/api/inbox/conversations/${second.id}/messages/**`, async route => { await waiting.promise; await route.fulfill({ json: { results: [], next: null, previous: null, count: 0 } }); });
  await page.route(`**/api/inbox/conversations/${second.id}/context/`, async route => { await waiting.promise; await route.fulfill({ json: secondContext }); });
  const list = page.getByTestId("inbox-conversation-list");
  const before = await list.boundingBox();
  try {
    await list.locator(`[data-conversation-id="${second.id}"]`).click();
    await expect(visibleLoaders(page)).toHaveCount(1);
    await expect(page.getByTestId("page-loading").filter({ visible: true })).toHaveCount(0);
    expect((await list.boundingBox())!.y).toBe(before!.y);
    await expect(visibleLoaders(page).locator(".platforma-loading__content")).toHaveCSS("opacity", "1");
    await page.screenshot({ animations: "disabled", path: info.outputPath("inbox-switch.png") });
    waiting.release();
    await expect(visibleLoaders(page)).toHaveCount(0);
    await list.locator(`[data-conversation-id="${first.id}"]`).click();
    await expect(composer).toHaveValue("Keep this unsent draft");
  } finally { waiting.release(); }
});
