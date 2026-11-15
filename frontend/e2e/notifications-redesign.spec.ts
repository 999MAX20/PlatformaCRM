import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable authentication fixture required"));

async function setup(page: Page, language = "ru") {
  const session = await crmSession(page);
  const notices = Array.from({ length: 9 }, (_, index) => ({
    id: 9000 + index, business: session.business, recipient: session.userId, client: null,
    client_name: `Тестовый клиент ${index + 1}`, channel: "system", kind: index === 0 ? "announcement" : "work",
    category: index % 2 ? "tasks" : "system", priority: "normal", text: index === 0 ? "Проверьте расписание команды" : `Обновление задачи ${index}`,
    message_key: "", action_url: "", action_label: "", send_at: new Date(Date.now() - index * 86400000 * 5).toISOString(),
    read_at: null as string | null, opened_at: null as string | null, acknowledged_at: null as string | null,
  }));
  const state = { listFailure: false, detailFailure: false, writeFailure: false, empty: false, manager: true, delay: 0, summaryFailure: false };
  const requests: URL[] = [];
  const writes: string[] = [];
  await page.route("**/api/notifications/**", async route => {
    const url = new URL(route.request().url());
    expect(url.searchParams.get("business")).toBe(String(session.business));
    if (url.pathname.endsWith("/summary/")) return state.summaryFailure ? route.fulfill({ status: 503, json: { detail: "Summary temporarily unavailable" } }) : route.fulfill({ json: { unread: notices.filter(n => !n.read_at).length, due: 0, urgent: 0, pending: 0, failed: 0, by_category: {}, can_manage_announcements: state.manager } });
    if (url.pathname.endsWith("/announcements/")) return route.fulfill({ json: { count: 0, results: [], next: null, previous: null, events_enabled: false } });
    const notice = notices.find(n => url.pathname.includes(`/${n.id}/`));
    if (route.request().method() === "POST") {
      writes.push(url.pathname);
      if (state.writeFailure) return route.fulfill({ status: 503, json: { detail: "Receipt temporarily unavailable" } });
      if (url.pathname.endsWith("/mark-all-read/")) { notices.forEach(n => n.read_at = new Date().toISOString()); return route.fulfill({ json: { updated: notices.length } }); }
      expect(notice).toBeTruthy();
      if (url.pathname.endsWith("/open/")) { notice!.opened_at = new Date().toISOString(); notice!.read_at = new Date().toISOString(); }
      if (url.pathname.endsWith("/mark-unread/")) notice!.read_at = null;
      if (url.pathname.endsWith("/mark-read/")) notice!.read_at = new Date().toISOString();
      if (url.pathname.endsWith("/acknowledge/")) notice!.acknowledged_at = new Date().toISOString();
      return route.fulfill({ json: notice });
    }
    if (notice) return state.detailFailure ? route.fulfill({ status: 403, json: { detail: "Source access revoked" } }) : route.fulfill({ json: notice });
    requests.push(url);
    if (state.delay) await new Promise(resolve => setTimeout(resolve, state.delay));
    if (state.listFailure) return route.fulfill({ status: 503, json: { detail: "Feed temporarily unavailable" } });
    let results = state.empty ? [] : [...notices];
    if (url.searchParams.get("unread") === "true") results = results.filter(n => !n.read_at);
    if (url.searchParams.get("awaiting_ack") === "true") results = results.filter(n => n.kind === "announcement" && !n.acknowledged_at);
    if (url.searchParams.get("category")) results = results.filter(n => n.category === url.searchParams.get("category"));
    const period = url.searchParams.get("period");
    if (period && period !== "all") results = results.filter(n => Date.parse(n.send_at) >= Date.now() - (period === "7d" ? 7 : 30) * 86400000);
    if (url.searchParams.get("order") === "oldest") results.reverse();
    const paginated = url.searchParams.has("page");
    const pageNumber = Number(url.searchParams.get("page") || 1);
    if (paginated && pageNumber > 1 && results.length <= (pageNumber - 1) * 5) return route.fulfill({ status: 404, json: { detail: "Invalid page." } });
    return route.fulfill({ json: { count: results.length, previous: pageNumber > 1 ? "previous" : null,
      next: paginated && results.length > pageNumber * 5 ? "next" : null, results: paginated ? results.slice((pageNumber - 1) * 5, pageNumber * 5) : results } });
  });
  await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/app/notifications");
  await expect(page.getByTestId("notification-feed-row").first()).toBeVisible();
  return { session, notices, state, requests, writes };
}

for (const [language, width, copy] of [["ru", 1440, ru], ["kk", 390, kk], ["en", 768, en]] as const) {
  test(`reference layout and receipt actions ${language} ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const { writes } = await setup(page, language);
    const controls = page.getByTestId("notification-list-controls");
    await expect(controls.getByText(copy["notification.period"], { exact: true })).toHaveCount(0);
    await expect(controls.getByText(copy["notification.order"], { exact: true })).toHaveCount(0);
    const periodBox = await controls.getByRole("combobox", { name: copy["notification.period"] }).boundingBox();
    const orderBox = await controls.getByRole("combobox", { name: copy["notification.order"] }).boundingBox();
    expect(Math.abs(periodBox!.y - orderBox!.y)).toBeLessThan(2);
    expect(periodBox!.x + periodBox!.width).toBeLessThan(orderBox!.x);
    await expect(page.getByTestId("notification-filters").getByRole("combobox")).toHaveCount(0);
    await page.screenshot({ path: info.outputPath(`header-${language}-${width}.png`), fullPage: true });
    const bell = page.getByTestId("header-notifications-trigger");
    await bell.focus(); await page.keyboard.press("Enter");
    await expect(page.getByTestId("notification-menu-row")).toHaveCount(6);
    const menu = page.getByTestId("notification-menu");
    await expect(menu.getByRole("link", { name: copy["notification.openCenter"] })).toBeInViewport();
    await page.screenshot({ path: info.outputPath(`bell-${language}-${width}.png`), fullPage: true });
    await page.keyboard.press("Escape"); await expect(bell).toBeFocused();
    await expect(menu).toHaveCount(0);
    const row = page.getByTestId("notification-feed-row").first().getByRole("button").first();
    await row.click();
    const inspector = page.getByTestId("notification-inspector");
    await expect(inspector).toHaveAttribute("role", "dialog");
    await expect(inspector).toHaveAttribute("aria-modal", "true");
    expect(await inspector.evaluate(element => getComputedStyle(element.parentElement!).backdropFilter)).toBe("none");
    await inspector.getByRole("button", { name: copy["common.close"], exact: true }).focus();
    await page.keyboard.press("Shift+Tab");
    expect(await inspector.evaluate(element => element.contains(document.activeElement))).toBeTruthy();
    await expect(inspector.getByRole("button", { name: copy["notification.acknowledge"], exact: true })).toBeEnabled();
    await expect(inspector.getByRole("button", { name: copy["notification.markUnread"], exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`center-${language}-${width}.png`), fullPage: true });
    const a11y = await new AxeBuilder({ page }).include('[data-testid="notifications-page"]').include('[data-testid="notification-inspector"]').analyze();
    expect(a11y.violations).toEqual([]);
    await inspector.getByRole("button", { name: copy["notification.markUnread"], exact: true }).click();
    await expect(inspector.getByRole("button", { name: copy["notification.markRead"], exact: true })).toBeEnabled();
    await inspector.getByRole("button", { name: copy["notification.markRead"], exact: true }).click();
    await inspector.getByRole("button", { name: copy["notification.acknowledge"], exact: true }).click();
    await expect(inspector.getByRole("status")).toContainText(copy["notification.acknowledged"]);
    await page.keyboard.press("Escape"); await expect(inspector).toHaveCount(0); await expect(row).toBeFocused();
    await row.click();
    await inspector.getByRole("button", { name: copy["common.close"], exact: true }).click();
    await expect(inspector).toHaveCount(0); await expect(row).toBeFocused();
    await page.getByRole("tab", { name: copy["notification.announcements"] }).click();
    await expect(page.getByRole("button", { name: copy["notification.publishAnnouncement"], exact: true })).toBeVisible();
    await page.getByRole("tab", { name: copy["notification.myFeed"] }).click();
    await page.getByRole("button", { name: copy["header.markAllRead"], exact: true }).click();
    await expect(page.getByRole("button", { name: copy["header.markAllRead"], exact: true })).toBeDisabled();
    await expect(page.getByText(copy["notification.readAllResult"].replace("{count}", "9"), { exact: true })).toHaveCount(0);
    expect(writes.filter(path => path.endsWith("/open/"))).toHaveLength(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  });
}

test("server filters, pagination, failures, recovery and access loss", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const { state, requests } = await setup(page);
  const filters = page.getByTestId("notification-filters");
  await filters.getByRole("button", { name: new RegExp(`^${ru["notification.filter.unread"]}`) }).click();
  await expect.poll(() => requests.at(-1)?.searchParams.get("unread")).toBe("true");
  await filters.getByRole("button", { name: ru["notification.category.tasks"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(4);
  await page.getByRole("combobox", { name: ru["notification.order"] }).click();
  await page.getByRole("option", { name: ru["notification.order.oldest"] }).click();
  await expect(page.getByTestId("notification-feed-row").first()).toContainText("Обновление задачи 7");
  await page.getByRole("combobox", { name: ru["notification.period"] }).click();
  await page.getByRole("option", { name: ru["notification.period.7d"] }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(1);
  await filters.getByRole("button", { name: ru["notification.filter.awaiting"], exact: true }).click();
  await expect(page.getByText(ru["header.noNotifications"], { exact: true })).toBeVisible();
  await filters.getByRole("button", { name: ru["notification.category.tasks"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(1);
  state.detailFailure = true;
  await page.getByTestId("notification-feed-row").first().getByRole("button").first().click();
  await expect(page.getByTestId("notification-inspector").getByTestId("inline-fallback")).toContainText(ru["fallback.permission.title"]);
  await expect(page.getByTestId("notification-inspector").getByRole("button", { name: ru["common.retry"], exact: true })).toHaveCount(0);
  await expect(page.getByTestId("notification-inspector").getByRole("button", { name: ru["notification.acknowledge"] })).toHaveCount(0);
  await page.getByTestId("notification-inspector").getByRole("button", { name: ru["common.close"], exact: true }).click();
  state.listFailure = true;
  await filters.getByRole("button", { name: ru["notification.filter.all"], exact: true }).first().click();
  await expect(page.getByTestId("notifications-page").getByRole("alert")).toBeVisible();
  state.listFailure = false;
  await page.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(2);
  await page.getByRole("combobox", { name: ru["notification.period"] }).click();
  await page.getByRole("option", { name: ru["notification.period.all"] }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(5);
  await page.getByRole("button", { name: ru["notification.next"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(4);
  await filters.getByRole("button", { name: ru["notification.filter.awaiting"], exact: true }).click();
  await expect.poll(() => requests.at(-1)?.searchParams.get("page")).toBe("1");
});

test("actual personal API open unread acknowledge and announcements", async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const session = await crmSession(page);
  const text = "Проверка редизайна: согласовать расписание команды";
  const response = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/notifications/announcements/?business=${session.business}`, {
    headers: session.headers, data: { text, priority: "normal", publication_key: crypto.randomUUID() },
  });
  expect(response.status(), await response.text()).toBe(201);
  await page.goto("/app/notifications");
  await page.getByTestId("notification-filters").getByRole("button", { name: ru["notification.filter.awaiting"], exact: true }).click();
  const row = page.getByTestId("notification-feed-row").filter({ hasText: text });
  await row.getByRole("button").first().click();
  const inspector = page.getByTestId("notification-inspector");
  await expect(inspector.getByRole("button", { name: ru["notification.markUnread"], exact: true })).toBeVisible();
  await inspector.getByRole("button", { name: ru["notification.markUnread"], exact: true }).click();
  await expect(inspector.getByRole("button", { name: ru["notification.markRead"], exact: true })).toBeVisible();
  await inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true }).click();
  await expect(inspector.getByRole("status")).toContainText(ru["notification.acknowledged"]);
  await expect(row).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("actual-api-center.png"), fullPage: true });
});

test("narrow layout, long content, mobile filters, zoom and announcement dialog", async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 740 });
  const { notices } = await setup(page);
  notices[0].text = "Проверка длинного уведомления: " + "расписание команды и перенос задачи ".repeat(50);
  await page.reload();
  await expect(page.getByTestId("notification-feed-row").first()).toBeVisible();
  const periodControl = page.getByRole("combobox", { name: ru["notification.period"] });
  await periodControl.focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("End");
  await page.keyboard.press("Enter");
  await expect(periodControl).toContainText(ru["notification.period.30d"]);
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Home");
  await page.keyboard.press("Enter");
  await expect(periodControl).toContainText(ru["notification.period.all"]);
  const orderControl = page.getByRole("combobox", { name: ru["notification.order"] });
  for (const control of [periodControl, orderControl]) {
    expect(await control.locator("span").first().evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  }
  expect(Math.abs((await periodControl.boundingBox())!.y - (await orderControl.boundingBox())!.y)).toBeLessThan(2);
  await page.screenshot({ path: info.outputPath("header-ru-320.png"), fullPage: true });
  const filters = page.getByTestId("notification-filters");
  await expect(filters).toBeHidden();
  await page.getByRole("button", { name: ru["notification.filters"], exact: true }).click();
  await expect(filters).toBeVisible();
  await filters.getByRole("button", { name: ru["notification.filter.awaiting"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(1);
  await page.getByRole("button", { name: ru["notification.filters"], exact: true }).click();
  await page.getByTestId("notification-feed-row").first().getByRole("button").first().click();
  const inspector = page.getByTestId("notification-inspector");
  await expect(inspector).toBeVisible();
  await page.screenshot({ path: info.outputPath("long-detail-320.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await page.keyboard.press("Escape"); await expect(inspector).toHaveCount(0);
  await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
  await page.getByTestId("header-notifications-trigger").click();
  await expect(page.getByTestId("notification-menu").getByRole("link", { name: ru["notification.openCenter"] })).toBeInViewport();
  const menuHeading = page.getByTestId("notification-menu").getByRole("heading");
  const titleBox = await menuHeading.locator("span").first().boundingBox();
  const countBox = await menuHeading.locator("span").last().boundingBox();
  expect(titleBox!.x + titleBox!.width).toBeLessThanOrEqual(countBox!.x);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
  await page.screenshot({ path: info.outputPath("bell-text-200-320.png"), fullPage: true });
  await page.getByTestId("notification-menu").getByRole("link", { name: ru["notification.openCenter"] }).click();
  await expect(page.getByTestId("notification-menu")).toHaveCount(0);
  await page.getByTestId("notification-feed-row").first().getByRole("button").first().click();
  await expect(inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true })).toBeEnabled();
  await inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true }).scrollIntoViewIfNeeded();
  expect(await inspector.getByRole("heading", { name: ru["header.notifications"], exact: true }).evaluate(element =>
    element.scrollWidth <= element.clientWidth + 1 && element.scrollHeight <= element.clientHeight + 1)).toBeTruthy();
  await page.screenshot({ path: info.outputPath("detail-actions-text-200-320.png"), fullPage: true });
  expect(await inspector.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBeTruthy();
  await inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true }).click();
  await expect(inspector.getByRole("status")).toContainText(ru["notification.acknowledged"]);
  await inspector.getByRole("button", { name: ru["common.close"], exact: true }).click();
  await expect(inspector).toHaveCount(0);
  await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
  await page.getByRole("tab", { name: ru["notification.announcements"] }).click();
  await page.getByRole("button", { name: ru["notification.publishAnnouncement"], exact: true }).click();
  const composer = page.getByTestId("announcement-composer");
  expect(await composer.evaluate(element => getComputedStyle(element.parentElement!).backdropFilter)).not.toBe("none");
  await expect(composer.getByRole("button", { name: ru["notification.publish"], exact: true })).toBeDisabled();
  await composer.getByRole("textbox", { name: ru["notification.announcementText"] }).fill("Проверка формы объявления");
  await expect(composer.getByRole("button", { name: ru["notification.publish"], exact: true })).toBeEnabled();
  const a11y = await new AxeBuilder({ page }).include('[data-testid="announcement-composer"]').analyze();
  expect(a11y.violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: ru["notification.publishAnnouncement"], exact: true })).toBeFocused();
});

test("loading empty summary recovery and disappearing last page", async ({ page }) => {
  const { state, notices, requests } = await setup(page);
  state.manager = false;
  state.delay = 1500;
  await page.reload();
  await expect(page.getByTestId("notification-feed-row").first()).toBeVisible();
  await expect(page.getByRole("tab", { name: ru["notification.announcements"] })).toHaveCount(0);
  const filters = page.getByTestId("notification-filters");
  await filters.getByRole("button", { name: new RegExp(`^${ru["notification.filter.unread"]}`) }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(0);
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(5);
  state.delay = 0;
  await page.getByRole("button", { name: ru["notification.next"], exact: true }).click();
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(4);
  notices.slice(5, 8).forEach(n => n.read_at = new Date().toISOString());
  await page.getByTestId("notification-feed-row").last().getByRole("button", { name: ru["notification.markRead"], exact: true }).click();
  await expect.poll(() => requests.at(-1)?.searchParams.get("page")).toBe("1");
  await expect(page.getByTestId("notification-feed-row")).toHaveCount(5);
  state.empty = true; state.summaryFailure = true;
  await page.reload();
  await expect(page.getByTestId("notifications-page").getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button", { name: ru["header.markAllRead"], exact: true })).toBeDisabled();
  state.summaryFailure = false;
  await page.getByTestId("notifications-page").getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(page.getByTestId("notifications-page").getByRole("alert")).toHaveCount(0);
  await expect(page.getByText(ru["header.noNotifications"], { exact: true })).toBeVisible();
});

test("bell source navigation waits for receipt success and retains retry", async ({ page }) => {
  const { notices, state } = await setup(page);
  notices[1].action_url = "/tasks";
  state.writeFailure = true;
  await page.getByTestId("header-notifications-trigger").click();
  const menu = page.getByTestId("notification-menu");
  await menu.getByRole("button", { name: /Обновление задачи 1/ }).click();
  await expect(menu.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/app\/notifications/);
  state.writeFailure = false;
  await menu.getByRole("button", { name: /Обновление задачи 1/ }).click();
  await expect(page).toHaveURL(/\/app\/tasks/);
  await expect(menu).toHaveCount(0);
});
