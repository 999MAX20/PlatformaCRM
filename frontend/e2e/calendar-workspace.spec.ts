import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { Appointment, BusinessRole, Task, TeamMember } from "../src/types";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const day = "2030-01-07";
test.use({ actionTimeout: 15_000 });
test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable calendar fixtures required"); test.setTimeout(180_000); });

async function fixture(page: Page, completePages = false) {
  const session = await crmSession(page);
  const stamp = Date.now();
  const branch = await session.create<{ id: number; name: string }>("branches", { name: `Calendar ${stamp}`, address: "Abay 25" });
  const service = await session.create<{ id: number; name: string }>("services", { name: `Visit ${stamp}`, duration_minutes: 30, price_from: "10000" });
  const resource = await session.create<{ id: number; name: string }>("resources", { name: `Doctor ${stamp}`, resource_type: "staff" });
  await session.action(`branches/${branch.id}/offers`, { service: service.id, duration_minutes: 30, price_from: "10000" });
  await session.action(`branches/${branch.id}/assignments`, { resource: resource.id, service_ids: [service.id] });
  for (const staff of [null, resource.id]) await session.action(`branches/${branch.id}/schedule`, { resource: staff, date: day, intervals: [{ start: "09:00", end: "18:00" }] });
  const slots = await session.read("appointments/available-slots", { business_id: session.business, branch_id: branch.id, resource_id: resource.id, service_id: service.id, date: day });
  const visits: Appointment[] = [];
  for (let index = 0; index < 3; index++) {
    const client = await session.create<{ id: number }>("clients", { full_name: `Patient ${stamp} ${index}` });
    visits.push(await session.create<Appointment>("appointments", { client: client.id, branch: branch.id, service: service.id, resource: resource.id, start_at: slots[index * 2].start_at }));
  }
  const tasks: Task[] = [];
  for (let index = 0; index < (completePages ? 51 : 7); index++) tasks.push(await session.create<Task>("tasks", { title: `Callback ${stamp} ${index}`, assignee: session.userId, due_at: `2030-01-07T${String(10 + index % 7).padStart(2, "0")}:00:00Z` }));
  if (completePages) {
    // Keep exactly three visits on the selected day; 48 more force a second API page.
    for (const date of ["2030-01-08", "2030-01-09", "2030-01-10"]) {
      for (const staff of [null, resource.id]) await session.action(`branches/${branch.id}/schedule`, { resource: staff, date, intervals: [{ start: "09:00", end: "18:00" }] });
      const available = await session.read("appointments/available-slots", { business_id: session.business, branch_id: branch.id, resource_id: resource.id, service_id: service.id, date });
      for (const slot of available.slice(0, 16)) await session.create("appointments", { client: visits[0].client, branch: branch.id, service: service.id, resource: resource.id, start_at: slot.start_at });
    }
  }
  return { ...session, branch, service, resource, visits, tasks };
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`month/week, complete pages, day/detail return and visit actions ${locale}`, async ({ page }, info) => {
    const s = await fixture(page, locale === "ru");
    const pages = new Set<string>();
    page.on("request", request => {
      const url = new URL(request.url());
      if (/\/api\/(appointments|tasks)\//.test(url.pathname)) pages.add(`${url.pathname}:${url.searchParams.get("page")}`);
    });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const path = `/app/calendar?date=${day}&view=month&branch=${s.branch.id}`;
    await page.goto(path);
    await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();
    if (locale === "ru") {
      expect(pages.has("/api/appointments/:2")).toBeTruthy();
      expect(pages.has("/api/tasks/:2")).toBeTruthy();
    }
    await expect(page.getByTestId("calendar-view-day")).toHaveCount(0);
    await expect(page.getByTestId("calendar-view-list")).toHaveCount(0);
    const cell = page.locator(`[data-calendar-day="${day}"]`);
    if (!info.project.name.startsWith("mobile")) await cell.hover();
    else await cell.focus();
    const preview = page.getByTestId("calendar-day-preview");
    await expect(preview).toBeVisible();
    await expect(preview).toContainText(s.visits[2].client_name!);
    await page.keyboard.press("Escape");
    await expect(preview).toBeHidden();
    await cell.focus();
    await cell.press("ArrowRight");
    await expect(page.locator('[data-calendar-day="2030-01-08"]')).toBeFocused();
    await page.keyboard.press("ArrowLeft");
    await expect(cell).toBeFocused();
    await page.keyboard.press("Enter");
    const inspector = page.getByTestId("calendar-day-inspector");
    await expect(inspector).toBeVisible();
    await expect(inspector.locator("[data-appointment-id]")).toHaveCount(3);
    for (const task of s.tasks) await expect(inspector.locator(`a[href="/app/tasks/${task.id}"]`)).toHaveCount(1);
    const visit = inspector.locator(`[data-appointment-id="${s.visits[0].id}"]`);
    await visit.click();
    await expect(page.getByTestId("calendar-appointment-detail")).toContainText(s.visits[0].client_name!);
    await inspector.getByRole("button", { name: copy["common.back"], exact: true }).click();
    await expect(visit).toBeFocused();
    await visit.press("Enter");
    await page.getByTestId("calendar-appointment-status-confirmed").click();
    await expect.poll(async () => (await s.read(`appointments/${s.visits[0].id}`)).status).toBe("confirmed");
    await page.getByTestId("calendar-appointment-status-cancelled").click();
    const reason = page.getByRole("dialog", { name: copy["appointments.statusReasonTitle"], exact: true });
    await expect(reason.getByRole("button", { name: copy["appointment.actionCancel"], exact: true })).toBeDisabled();
    await page.keyboard.press("Escape");
    await expect(inspector).toBeVisible();
    await page.getByTestId("calendar-reschedule-action").click();
    const form = page.getByTestId("appointment-reschedule-form");
    await form.getByRole("combobox", { name: new RegExp("^" + copy["appointment.time"]) }).click();
    await page.getByRole("option").last().click();
    await form.getByTestId("appointment-reschedule-submit").click();
    await expect(form).toBeHidden();
    await expect.poll(async () => (await s.read(`appointments/${s.visits[0].id}`)).start_at).not.toBe(s.visits[0].start_at);
    await expect(page.getByTestId("calendar-reschedule-action")).toBeFocused();
    await page.screenshot({ path: info.outputPath(`calendar-detail-${locale}.png`), fullPage: true });
    await inspector.getByRole("button", { name: copy["common.back"], exact: true }).click();
    await page.keyboard.press("Escape");
    await expect(inspector).toBeHidden();
    await expect(cell).toBeFocused();
    await page.getByTestId("calendar-view-week").click();
    await expect(page.getByTestId("calendar-board-week")).toBeVisible();
    await expect(page.locator("[data-calendar-day]")).toHaveCount(7);
    await page.screenshot({ path: info.outputPath(`calendar-week-${locale}.png`), fullPage: true });
    await page.getByTestId("calendar-period-picker").click();
    const picker = page.getByTestId("calendar-date-picker");
    await expect(picker.getByRole("combobox", { name: copy["crmFilters.year"], exact: true })).toBeVisible();
    await picker.locator('[data-date="2030-01-07"]').focus();
    await page.keyboard.press("ArrowRight");
    await expect(picker.locator('[data-date="2030-01-08"]')).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(picker).toBeHidden();
    await expect(page).toHaveURL(/date=2030-01-08/);
    await page.goto(`/app/calendar?date=2030-01-31&view=month&branch=${s.branch.id}`);
    await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();
    await page.route(/\/api\/appointments\/\?.*start_from=2030-02-01/, async route => {
      await new Promise(resolve => setTimeout(resolve, 350));
      await route.continue();
    });
    await page.locator('[data-calendar-day="2030-01-31"]').focus();
    await page.keyboard.press("ArrowRight");
    await expect(page).toHaveURL(/date=2030-02-01/);
    await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();
    await expect(page.locator('[data-calendar-day="2030-02-01"]')).toBeFocused();
    await page.goto(`${path}&service=${s.service.id}&resource=${s.resource.id}&status=confirmed`);
    await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();
    await cell.click();
    await expect(inspector.locator("[data-appointment-id]")).toHaveCount(1);
    await inspector.locator("[data-appointment-id]").click();
    await inspector.getByRole("button", { name: copy["calendar.openCard"], exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/app/calendar/${s.visits[0].id}$`));
    expect((await s.read(`appointments/${s.visits[0].id}`)).branch).toBe(s.branch.id);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(2);
  });
}

test("failed calendar load recovers without presenting an empty day", async ({ page }) => {
  await crmSession(page);
  let fail = true;
  await page.route(/\/api\/appointments\/\?/, route => fail ? route.fulfill({ status: 503, json: { detail: "Calendar temporarily unavailable" } }) : route.continue());
  await page.goto(`/app/calendar?date=${day}&view=month`);
  await expect(page.getByTestId("calendar-error-state")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("calendar-board-month")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(page.getByTestId("calendar-board-month")).toBeVisible();
  await page.locator('[data-calendar-day="2030-01-31"]').click();
  const inspector = page.getByTestId("calendar-day-inspector");
  await expect(inspector.getByText(ru["calendar.dayEmpty"], { exact: true })).toBeVisible();
  await inspector.getByRole("button", { name: ru["calendar.nextDay"], exact: true }).click();
  await expect(page).toHaveURL(/date=2030-02-01/);
  await page.keyboard.press("Escape");
  await expect(page.locator('[data-calendar-day="2030-02-01"]')).toBeFocused();
});

test("view-only calendar works without optional task/client/lead access and denies writes", async ({ page }) => {
  const s = await fixture(page);
  const member = (await s.list<TeamMember>("team/members")).find(item => item.role === "operator")!;
  const role = (await s.list<BusinessRole>("team/roles")).find(item => item.id === member.business_role || item.preset_key === member.role)!;
  const assigned = await page.request.patch(`${api}/api/team/members/${member.id}/`, { headers: s.headers, data: { business_role: role.id } });
  expect(assigned.ok(), await assigned.text()).toBeTruthy();
  for (const permission of role.permissions.filter(item => ["appointments", "tasks", "clients", "leads"].includes(item.resource))) {
    const response = await page.request.patch(`${api}/api/team/role-permissions/${permission.id}/`, { headers: s.headers, data: { is_allowed: permission.resource === "appointments" && permission.action === "view", scope: "business" } });
    expect(response.ok(), await response.text()).toBeTruthy();
  }
  await s.action("branches/member-access", { member: member.id, all_branches: false, branch_ids: [s.branch.id] });
  await page.context().clearCookies();
  await page.evaluate(() => localStorage.clear());
  const operator = await crmSession(page, member.user.email);
  const profile = await operator.read("auth/me");
  expect(profile.effective_permissions[String(s.business)].some((permission: { resource: string; action: string }) => permission.resource === "appointments" && permission.action === "update")).toBe(false);
  const optional: string[] = [];
  page.on("request", request => { if (/\/api\/(tasks|clients|leads)\//.test(request.url())) optional.push(request.url()); });
  await page.goto(`/app/calendar?date=${day}&view=month&branch=${s.branch.id}`);
  await expect(page.getByTestId("calendar-workspace-ready")).toBeVisible();
  await page.locator(`[data-calendar-day="${day}"]`).click();
  const inspector = page.getByTestId("calendar-day-inspector");
  await expect(inspector.getByText(ru["calendar.tasksToday"] + ":", { exact: false })).toHaveCount(0);
  await inspector.locator(`[data-appointment-id="${s.visits[0].id}"]`).click();
  await expect(page.getByTestId("calendar-appointment-detail")).toContainText(s.visits[0].client_name!);
  await expect(page.getByTestId("calendar-reschedule-action")).toHaveCount(0);
  await expect(page.getByTestId("calendar-appointment-status-confirmed")).toHaveCount(0);
  await expect(page.getByRole("button", { name: ru["calendar.newBooking"], exact: true })).toHaveCount(0);
  expect(optional).toEqual([]);
  const denied = await page.request.post(`${api}/api/appointments/${s.visits[0].id}/confirm/`, { headers: operator.headers });
  expect(denied.status()).toBe(403);
  expect((await s.read(`appointments/${s.visits[0].id}`)).status).toBe("created");
});
