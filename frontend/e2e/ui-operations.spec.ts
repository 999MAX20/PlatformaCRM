import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const queueUrl = /\/api\/work-queues\/(?:\?.*)?$/;
const leadUrl = /\/api\/leads\/(?:\?.*)?$/;
const inboxUrl = /\/api\/inbox\/conversations\/(?:\?.*)?$/;
test.use({ actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(120_000);
});

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(2);
  await expect(page.getByText("Unexpected Application Error")).toHaveCount(0);
}

test("calendar arrows follow view and period labels across month and year boundaries", async ({ page }, info) => {
  await crmSession(page);
  await page.goto("/app/calendar?date=2026-12-31&view=day");
  await page.getByRole("button", { name: ru["calendar.nextDay"], exact: true }).click();
  await expect(page).toHaveURL(/date=2027-01-01/);
  await page.getByTestId("calendar-view-week").click();
  await expect(page.getByTestId("calendar-view-week")).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: ru["calendar.previousWeek"], exact: true }).click();
  await expect(page).toHaveURL(/date=2026-12-25/);
  await page.goto("/app/calendar?date=2028-01-31&view=month");
  await page.getByRole("button", { name: ru["calendar.nextMonth"], exact: true }).click();
  await expect(page).toHaveURL(/date=2028-02-29/);
  for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/calendar?date=2026-12-31&view=week");
    const previous = page.getByRole("button", { name: copy["calendar.previousWeek"], exact: true });
    await previous.focus();
    await expect(previous).toBeFocused();
    await previous.press("Enter");
    await expect(page).toHaveURL(/date=2026-12-24/);
    await expect(page.getByTestId("calendar-view-week")).toHaveAttribute("aria-pressed", "true");
    await noOverflow(page);
    await page.screenshot({ path: info.outputPath(`calendar-${locale}.png`), fullPage: true });
  }
});

test("leads distinguish empty, filtered and failed loads with one create action and compact form", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.route(leadUrl, route => route.request().method() === "GET"
    ? route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }) : route.continue());
  await page.goto("/app/leads");
  await expect(page.getByText(ru["leads.emptyTitle"], { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: ru["leads.create"], exact: true })).toHaveCount(1);
  await expect(page.getByLabel(ru["leads.selectAll"], { exact: true })).toHaveCount(0);
  await expect(page.getByText(/0–0|0-0/)).toHaveCount(0);
  await expect(page.getByRole("button", { name: ru["leads.filters"], exact: true })).toHaveCount(1);
  await page.getByTestId("leads-search-input").fill("No matching synthetic lead");
  await expect(page.getByText(ru["leads.emptyFilteredTitle"], { exact: true })).toBeVisible();
  await page.getByRole("button", { name: ru["tasks.resetFilters"], exact: true }).click();
  await expect(page.getByTestId("leads-search-input")).toHaveValue("");
  await page.getByRole("button", { name: ru["leads.create"], exact: true }).click();
  const form = page.getByTestId("lead-action-form");
  await expect(form).toBeVisible();
  const clients = await session.list<{ id: number; full_name: string }>("clients");
  await form.getByRole("combobox", { name: new RegExp(`^${ru["appointment.client"]} `) }).click();
  await page.getByRole("option").filter({ hasText: clients[0].full_name }).first().click();
  await form.getByRole("textbox", { name: ru["leadForm.message"], exact: true }).fill("Synthetic compact form draft");
  await page.screenshot({ path: info.outputPath("lead-form.png"), fullPage: true });
  await noOverflow(page);
  await page.getByTestId("lead-action-submit").click();
  await expect(form).toHaveCount(0);
  await page.unroute(leadUrl);
  await page.route(leadUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } }));
  await page.reload();
  await expect(page.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  await expect(page.getByText(ru["leads.emptyTitle"], { exact: true })).toHaveCount(0);
  await page.unroute(leadUrl);
  await page.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(page.getByTestId("leads-workspace-ready")).toBeVisible();
});

test("deals show a scheduled next action and an honest empty stage", async ({ page }, info) => {
  const session = await crmSession(page);
  const client = (await session.list<{ id: number }>("clients"))[0];
  const pipeline = (await session.list<{ id: number }>("pipelines"))[0];
  const stage = (await session.list<{ id: number; pipeline: number; is_won: boolean; is_lost: boolean }>("pipeline-stages"))
    .find(item => item.pipeline === pipeline.id && !item.is_won && !item.is_lost)!;
  const deal = await session.create<{ id: number }>("deals", { client: client.id, pipeline: pipeline.id, stage: stage.id,
    title: "Synthetic scheduled next step", amount: "12500", next_action_at: "2027-01-10T09:30:00Z" });
  await page.goto(`/app/deals?pipeline=${pipeline.id}`);
  const card = page.locator("article").filter({ hasText: "Synthetic scheduled next step" });
  await expect(card.getByText(ru["deals.nextAction"], { exact: true })).toBeVisible();
  await expect(card.getByText(ru["deals.noTasksFilter"], { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: new RegExp(ru["deals.hot"]) }).first()).toBeVisible();
  await page.screenshot({ path: info.outputPath("deals.png"), fullPage: true });
  await page.goto(`/app/deals?pipeline=${pipeline.id}&quick=no_tasks`);
  await expect(page.locator("article").filter({ hasText: "Synthetic scheduled next step" })).toHaveCount(0);
  expect((await session.read(`deals/${deal.id}`)).next_action_at).toContain("2027-01-10");
  await noOverflow(page);
});

test("Inbox restored layout supports filters and a populated conversation keeps its draft", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.route(inboxUrl, route => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await page.goto("/app/conversations");
  await expect(page.getByText(ru["conversations.emptyTitle"], { exact: true })).toHaveCount(1);
  if (info.project.name !== "mobile-chromium") {
    await expect(page.getByText(ru["conversations.selectDialog"], { exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: ru["conversations.advancedFilters"], exact: true }).click();
  await expect(page.getByRole("combobox", { name: ru["conversations.agent"], exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: new RegExp(`^${ru["conversations.agent"]} `) })).toBeVisible();
  await page.getByRole("button", { name: ru["conversations.advancedFilters"], exact: true }).click();
  await page.screenshot({ path: info.outputPath("inbox-empty.png"), fullPage: true });
  await noOverflow(page);
  await page.goto("/app/conversations?unread=true");
  await expect(page.getByText(ru["conversations.emptyTitle"], { exact: true })).toBeVisible();
  await page.unroute(inboxUrl);
  const conversations = await session.list<{ id: number }>("inbox/conversations");
  await page.goto(`/app/conversations?conversation=${conversations[0].id}`);
  const reply = page.getByPlaceholder(ru["conversations.replyPlaceholder"]);
  await expect(reply).toBeVisible();
  await reply.fill("Synthetic unsent draft");
  await page.screenshot({ path: info.outputPath("inbox-filled.png"), fullPage: true });
  await expect(reply).toHaveValue("Synthetic unsent draft");
  await noOverflow(page);
});

test("business settings retain drafts across groups, reveal invalid fields and recover a failed save", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.goto("/app/settings#business-profile");
  const root = page.getByTestId("settings-workspace-ready");
  if (await root.locator("aside nav").isVisible()) {
    const navigationGroup = root.locator("aside nav > div").filter({ has: page.locator('a[href="#business-profile"]') });
    const toggle = root.locator("aside nav").getByRole("button", { name: (await navigationGroup.getByRole("button").innerText()).trim(), exact: true });
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(root.locator('aside nav a[href="#business-profile"]')).toHaveCount(0);
    await toggle.click();
    await expect(root.locator('aside nav a[href="#business-profile"]')).toBeVisible();
  }
  const group = (key: string) => root.getByRole("button", { name: ru[`businessForm.group.${key}`], exact: true });
  const phone = root.getByRole("textbox", { name: ru["businessForm.phone"], exact: true });
  await phone.fill("+77001234567");
  await group("appearance").click();
  const logo = root.getByRole("textbox", { name: new RegExp(`^${ru["businessForm.brandLogoUrl"]}`) });
  await logo.fill("invalid-url");
  await group("profile").click();
  await expect(phone).toHaveValue("+77001234567");
  await root.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect(group("appearance")).toHaveAttribute("aria-pressed", "true");
  await expect(logo).toBeFocused();
  await logo.fill("");
  await group("appointments").focus();
  await group("appointments").press("Enter");
  await expect(root.getByRole("spinbutton", { name: ru["businessForm.bookingBufferMinutes"], exact: true })).toBeVisible();
  await group("finance").click();
  await expect(root.getByRole("textbox", { name: ru["businessForm.legalName"], exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("settings-finance.png"), fullPage: true });
  const businessUrl = `**/api/businesses/${session.business}/`;
  await page.route(businessUrl, route => ["PATCH", "PUT"].includes(route.request().method())
    ? route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } }) : route.continue());
  await root.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect(root.getByRole("alert").first()).toBeVisible();
  await group("profile").click();
  await expect(phone).toHaveValue("+77001234567");
  await page.unroute(businessUrl);
  const save = page.waitForResponse(response => response.url().endsWith(`/api/businesses/${session.business}/`) && response.request().method() === "PATCH");
  await root.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  expect((await save).ok()).toBeTruthy();
  expect((await session.read(`businesses/${session.business}`)).phone).toBe("+77001234567");
  await page.reload();
  await expect(phone).toHaveValue("+77001234567");
  await noOverflow(page);
  expect((await new AxeBuilder({ page }).include("#business-profile").analyze()).violations).toEqual([]);
});

test("dashboard distinguishes full totals, empty data and failed queues with working entity links", async ({ page }, info) => {
  const session = await crmSession(page);
  for (let index = 0; index < 9; index++) await session.create("tasks", { title: `Synthetic overdue ${index}`, due_at: "2026-01-01T09:00:00Z", assignee: session.userId });
  const data = await session.read("work-queues", { business: session.business, limit: 8 });
  await page.goto("/app");
  await expect(page.getByTestId("dashboard-metric-overdue_tasks").locator(".tabular-nums")).toHaveText(String(data.summary.overdue_tasks));
  expect(data.summary.overdue_tasks).toBeGreaterThan(8);
  await expect(page.getByTestId("dashboard-attention-item")).toHaveCount(8);
  await page.getByRole("button", { name: ru["dashboard.showMore"], exact: true }).click();
  await expect(page.getByTestId("dashboard-attention-item")).toHaveCount(Math.min(16, data.summary.total_attention));
  await page.screenshot({ path: info.outputPath("dashboard-filled.png"), fullPage: true });
  await noOverflow(page);
  const first = page.getByTestId("dashboard-attention-item").first();
  const href = await first.getAttribute("href");
  await first.click();
  await expect(page).toHaveURL(new RegExp(href!.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  await page.route(queueUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic queue failure" } }));
  await page.goto("/app");
  const error = page.getByTestId("dashboard-priority-error");
  await expect(error).toBeVisible();
  await expect(page.getByTestId("dashboard-metric-overdue_tasks")).toHaveCount(0);
  await expect(page.getByText(ru["dashboard.noPrioritiesTitle"], { exact: true })).toHaveCount(0);
  await page.unroute(queueUrl);
  await error.getByRole("button").click();
  await expect(page.getByTestId("dashboard-operations")).toBeVisible();
  await page.route(queueUrl, route => route.fulfill({ json: { ...data, attention: [],
    summary: Object.fromEntries(Object.keys(data.summary).map(key => [key, 0])),
    queues: Object.fromEntries(Object.keys(data.queues).map(key => [key, []])) } }));
  for (const locale of ["ru", "kk", "en"]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.reload();
    await expect(page.getByTestId("dashboard-metric-overdue_tasks").locator(".tabular-nums")).toHaveText("0");
    await page.screenshot({ path: info.outputPath(`dashboard-empty-${locale}.png`), fullPage: true });
    await noOverflow(page);
  }
});
