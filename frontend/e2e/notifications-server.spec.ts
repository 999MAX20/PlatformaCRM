import { execFileSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import type { Notification } from "../src/types";

type Fixture = {
  business: number; foreignBusiness: number; owner: number; staff: number;
  rows: { id: number; text: string }[]; work: number; task: number; excluded: number[];
};
const api = process.env.E2E_API_BASE_URL;
type Session = Awaited<ReturnType<typeof crmSession>>;

function seed(mode: "dated" | "receipts"): Fixture {
  return JSON.parse(execFileSync(process.env.E2E_PYTHON!, ["e2e/support/seed-notification-server.py", mode],
    { encoding: "utf8", windowsHide: true }).trim().split("\n").at(-1)!);
}

async function select(page: Page, key: string, option: string) {
  await page.getByRole("combobox", { name: ru[key] }).click();
  await page.getByRole("option", { name: ru[option], exact: true }).click();
}

async function state(session: Session, id: number): Promise<Notification> {
  return session.read(`notifications/${id}`, { business: session.business });
}

async function summary(session: Session) {
  return session.read("notifications/summary", { business: session.business, surface: "bell" });
}

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable authentication fixture required");
  test.setTimeout(60000);
});

test("real feed periods, ordering, category, pagination and read-all scope", async ({ page }, info) => {
  const fixture = seed("dated");
  const session = await crmSession(page);
  await page.goto("/app/notifications");
  const feed = page.getByTestId("notification-feed-row");
  await expect(feed).toHaveCount(50);
  expect((await summary(session)).unread).toBe(56);
  const initial = await session.read("notifications", { business: fixture.business, surface: "bell" });
  expect(initial.count).toBe(56);
  expect(initial.results.some((row: Notification) => fixture.excluded.includes(Number(row.id)))).toBeFalsy();
  expect(initial.results.find((row: Notification) => row.id === fixture.work).text).toBe("");
  await expect(page.getByText("PRIVATE WORK SNAPSHOT")).toHaveCount(0);
  await page.getByRole("button", { name: ru["notification.next"], exact: true }).click();
  await expect(feed).toHaveCount(6);
  await select(page, "notification.period", "notification.period.7d");
  await expect(feed).toHaveCount(8);
  await expect(page.getByRole("navigation", { name: ru["notification.pages"] })).toHaveCount(0);
  const filters = page.getByTestId("notification-filters");
  await filters.getByRole("button", { name: ru["notification.category.system"], exact: true }).click();
  await expect(feed).toHaveCount(7);
  await select(page, "notification.order", "notification.order.oldest");
  await expect(feed.first()).toContainText(fixture.rows[6].text);
  await select(page, "notification.period", "notification.period.30d");
  await expect(feed).toHaveCount(30);
  await expect(feed.first()).toContainText(fixture.rows[29].text);
  await select(page, "notification.period", "notification.period.all");
  await expect(feed).toHaveCount(50);
  await expect(feed.first()).toContainText(fixture.rows[54].text);
  await select(page, "notification.period", "notification.period.7d");
  await expect(feed).toHaveCount(7);
  await page.screenshot({ path: info.outputPath("server-period-order.png"), fullPage: true });
  await page.getByRole("button", { name: ru["header.markAllRead"], exact: true }).click();
  await expect.poll(async () => (await summary(session)).unread).toBe(0);
  expect((await state(session, fixture.rows[54].id)).read_at).toBeTruthy();
  expect((await state(session, fixture.rows[54].id)).acknowledged_at).toBeNull();
  await expect(page.getByRole("button", { name: ru["header.markAllRead"], exact: true })).toBeDisabled();
  await expect(page.getByText(/Отмечено прочитанными/)).toHaveCount(0);
});

test("real bell finds older unread beyond page one and retries writes safely", async ({ page }, info) => {
  const fixture = seed("dated");
  const session = await crmSession(page);
  const readAll = await page.request.post(`${api}/api/notifications/mark-all-read/?business=${fixture.business}`,
    { headers: session.headers, data: {} });
  expect(readAll.ok()).toBeTruthy();
  const unread = await page.request.post(`${api}/api/notifications/${fixture.rows[54].id}/mark-unread/?business=${fixture.business}`,
    { headers: session.headers, data: {} });
  expect(unread.ok()).toBeTruthy();
  await page.goto("/app/notifications");
  const bell = page.getByTestId("header-notifications-trigger");
  await expect(bell).toContainText("1");
  await bell.click();
  const menu = page.getByTestId("notification-menu");
  await expect(menu.getByText(fixture.rows[54].text, { exact: true })).toBeVisible();
  await expect(page.getByTestId("notification-menu-row")).toHaveCount(6);
  let fail = true;
  await page.route(`**/api/notifications/${fixture.rows[54].id}/mark-read/**`, async route => {
    if (fail) { fail = false; return route.fulfill({ status: 503, json: { detail: "Temporary transport failure" } }); }
    await route.continue();
  });
  await menu.getByRole("button", { name: ru["notification.markRead"], exact: true }).click();
  await expect(menu.getByRole("alert")).toBeVisible();
  expect((await state(session, fixture.rows[54].id)).read_at).toBeNull();
  await menu.getByRole("button", { name: ru["notification.markRead"], exact: true }).click();
  await expect.poll(async () => (await summary(session)).unread).toBe(0);
  expect((await state(session, fixture.rows[54].id)).opened_at).toBeNull();
  expect((await state(session, fixture.rows[54].id)).acknowledged_at).toBeNull();
  await expect(menu.getByRole("alert")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("server-bell-read.png"), fullPage: true });
  await page.keyboard.press("Escape");
  await expect(bell).toBeFocused();
});

test("real announcement receipts are private, permissions hold and revoke removes access", async ({ page, browser }, info) => {
  const fixture = seed("receipts");
  const owner = await crmSession(page);
  const staffContext = await browser.newContext({ baseURL: process.env.E2E_BASE_URL });
  const staffPage = await staffContext.newPage();
  try {
    const staff = await crmSession(staffPage, "business_specialist@example.com");
    const notice = fixture.rows[0];
    const deniedPublish = await staffPage.request.post(`${api}/api/notifications/announcements/?business=${fixture.business}`,
      { headers: staff.headers, data: { text: "Unauthorized", priority: "normal", publication_key: crypto.randomUUID() } });
    expect(deniedPublish.status()).toBe(403);
    const foreign = await staffPage.request.get(`${api}/api/notifications/?business=${fixture.foreignBusiness}&surface=bell`, { headers: staff.headers });
    expect(foreign.status()).toBe(403);
    const earlyAck = await staffPage.request.post(`${api}/api/notifications/${notice.id}/acknowledge/?business=${fixture.business}`,
      { headers: staff.headers, data: {} });
    expect(earlyAck.status()).toBe(409);
    await staffPage.goto("/app/notifications");
    await expect(staffPage.getByRole("tab", { name: ru["notification.announcements"] })).toHaveCount(0);
    const staffRow = staffPage.getByTestId("notification-feed-row").filter({ hasText: notice.text });
    await staffRow.getByRole("button").first().click();
    const inspector = staffPage.getByTestId("notification-inspector");
    await expect(inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true })).toBeEnabled();
    expect((await state(staff, notice.id)).read_at).toBeTruthy();
    expect((await state(owner, notice.id)).read_at).toBeNull();
    await inspector.getByRole("button", { name: ru["notification.acknowledge"], exact: true }).click();
    await expect(inspector.getByRole("status")).toContainText(ru["notification.acknowledged"]);
    const firstAck = (await state(staff, notice.id)).acknowledged_at;
    const repeated = await staffPage.request.post(`${api}/api/notifications/${notice.id}/acknowledge/?business=${fixture.business}`,
      { headers: staff.headers, data: {} });
    expect((await repeated.json()).acknowledged_at).toBe(firstAck);
    expect((await state(owner, notice.id)).acknowledged_at).toBeNull();
    await inspector.getByRole("button", { name: ru["notification.markUnread"], exact: true }).click();
    await expect(inspector.getByRole("button", { name: ru["notification.markRead"], exact: true })).toBeEnabled();
    expect((await state(staff, notice.id)).acknowledged_at).toBe(firstAck);
    await page.goto("/app/notifications");
    await page.getByRole("tab", { name: ru["notification.announcements"] }).click();
    const announcement = page.getByRole("article").filter({ hasText: notice.text });
    await announcement.getByRole("button", { name: ru["notification.monitoring"] }).click();
    const monitor = page.getByTestId("announcement-monitor");
    const recipients = await owner.read(`notifications/${notice.id}/announcement-recipients`, { business: fixture.business });
    expect(recipients.announcement.acknowledged_count).toBe(1);
    expect(recipients.results.find((row: { user: number }) => row.user === fixture.staff).acknowledged_at).toBe(firstAck);
    await page.screenshot({ path: info.outputPath("server-private-receipts.png"), fullPage: true });
    await monitor.getByRole("button", { name: ru["notification.revoke"], exact: true }).click();
    await monitor.getByRole("button", { name: ru["notification.revoke"], exact: true }).click();
    await expect(monitor.getByRole("status")).toContainText(ru["notification.revoked"]);
    const revoked = await staffPage.request.get(`${api}/api/notifications/${notice.id}/?business=${fixture.business}`, { headers: staff.headers });
    expect(revoked.status()).toBe(404);
    await staffPage.reload();
    const remaining = await staff.read("notifications", { business: fixture.business, surface: "bell" });
    await expect(staffPage.getByTestId("notification-feed-row")).toHaveCount(remaining.count);
    await expect(staffPage.getByText(notice.text, { exact: true })).toHaveCount(0);
    await staffPage.getByTestId("header-notifications-trigger").click();
    await expect(staffPage.getByTestId("notification-menu").getByText(notice.text, { exact: true })).toHaveCount(0);
  } finally {
    await staffContext.close();
  }
});
