import { expect, test, type Locator, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import type { Appointment, BusinessRole, Task, TeamMember } from "../src/types";
import type { InboxContext, InboxConversation } from "../src/api/inbox";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const day = "2030-01-07";
test.use({ timezoneId: "UTC", actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable daily-cycle fixtures required");
  test.setTimeout(300_000);
});

async function choose(page: Page, scope: Page | Locator, label: string, option: string) {
  await scope.getByRole("combobox", { name: new RegExp("^" + label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}
async function contextPanel(page: Page) {
  const trigger = page.getByRole("button", { name: ru["conversations.aboutClient"], exact: true });
  if (await trigger.getAttribute("aria-expanded") !== "true") await trigger.click();
  return page.getByTestId("inbox-customer-context").filter({ visible: true });
}

test("R01 administrator follows one customer from Inbox through visit, receipt and history", async ({ page }, info) => {
  // Owner prepares only synthetic configuration. All operational mutations below use the administrator UI.
  const owner = await crmSession(page);
  const marker = `R01 ${Date.now()}`;
  const branch = await owner.create<{ id: number; name: string }>("branches", { name: `${marker} branch`, address: "Abay 25" });
  const service = await owner.create<{ id: number; name: string }>("services", { name: `${marker} visit`, duration_minutes: 30 });
  const staff = await owner.create<{ id: number; name: string }>("resources", { name: `${marker} doctor`, resource_type: "staff" });
  await owner.action(`branches/${branch.id}/offers`, { service: service.id, duration_minutes: 30, price_from: "1250.50" });
  await owner.action(`branches/${branch.id}/assignments`, { resource: staff.id, service_ids: [service.id] });
  for (const resource of [null, staff.id]) await owner.action(`branches/${branch.id}/schedule`, { resource, date: day, intervals: [{ start: "09:00", end: "18:00" }] });
  const member = (await owner.list<TeamMember>("team/members")).find(m => m.user.email === "business_manager@example.com")!;
  const role = (await owner.list<BusinessRole>("team/roles")).find(r => r.preset_key === "admin")!;
  expect(role).toBeTruthy();
  const assigned = await page.request.patch(`${api}/api/team/members/${member.id}/`, { headers: owner.headers, data: { role: "admin", business_role: role.id } });
  expect(assigned.ok(), await assigned.text()).toBeTruthy();
  await owner.action("branches/member-access", { member: member.id, all_branches: false, branch_ids: [branch.id] });
  const finance = await page.request.patch(`${api}/api/businesses/${owner.business}/`, { headers: owner.headers, data: { financial_source_mode: "manual" } });
  expect(finance.ok(), await finance.text()).toBeTruthy();
  const conversation = (await owner.list<InboxConversation>("inbox/conversations"))[0];
  const initial: InboxContext = await owner.read(`inbox/conversations/${conversation.id}/context`);
  const client = initial.client.data!;
  const lead = initial.lead.data!;
  expect(client).toBeTruthy(); expect(lead).toBeTruthy();
  expect(initial.deal.state).toBe("empty");
  const named = await page.request.patch(`${api}/api/clients/${client.id}/`, { headers: owner.headers, data: { full_name: marker } });
  expect(named.ok()).toBeTruthy();
  expect((await owner.list<{ is_active: boolean }>("automation-rules")).filter(rule => rule.is_active)).toHaveLength(0);
  await page.context().clearCookies();
  await page.evaluate(() => localStorage.clear());
  const s = await crmSession(page, member.user.email);
  expect(s.userId).toBe(member.user.id);
  const receipts: Array<{ control: string; path: string; id: number; status: number }> = [];
  async function action(control: string, path: string, click: () => Promise<void>) {
    const pending = page.waitForResponse(r => r.request().method() === "POST" && new URL(r.url()).pathname === `/api/${path}/`);
    await click();
    const response = await pending;
    expect(response.ok(), await response.text()).toBeTruthy();
    const entity = await response.json();
    receipts.push({ control, path, id: entity.id, status: response.status() });
    return entity;
  }

  await page.goto(`/app/conversations/${conversation.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await composer.fill(`${marker} unsent reply`);
  await expect.poll(async () => (await s.read("inbox/conversations/summary")).unread_messages).toBe(0);
  await expect(page.locator("header").getByText(ru["header.chatToastTitle"], { exact: true })).toBeHidden();
  await action("inbox.assign", `inbox/conversations/${conversation.id}/assign`, async () => {
    const take = page.getByRole("button", { name: ru["conversations.takeDialog"], exact: true });
    if (await take.isVisible()) await take.click();
    else {
      await page.getByRole("button", { name: ru["conversations.dialogActions"], exact: true }).click();
      await page.getByRole("menuitem", { name: ru["conversations.takeDialog"], exact: true }).click();
    }
  });
  let panel = await contextPanel(page);
  await panel.locator(`a[href="${client.href}"]`).click();
  await expect(page.getByText(marker, { exact: true }).first()).toBeVisible();
  await page.getByTestId("client-edit-action").click();
  const edit = page.getByRole("dialog", { name: ru["clients.editTitle"], exact: true });
  await edit.getByRole("textbox", { name: ru["clients.notes"], exact: true }).fill(`${marker} afternoon callback`);
  await edit.getByTestId("client-action-submit").click();
  await expect(edit).toBeHidden();
  expect((await s.read(`clients/${client.id}`)).notes).toBe(`${marker} afternoon callback`);
  await page.goBack();
  await expect(composer).toHaveValue(`${marker} unsent reply`);
  panel = await contextPanel(page);
  await panel.locator(`a[href="${lead.href}"]`).click();
  await action("lead.contact", `leads/${lead.id}/mark-contacted`, () => page.locator('[data-crm-action-id="contacted"]').click());
  expect((await s.read(`leads/${lead.id}`)).status).toBe("contacted");
  await page.goBack();
  panel = await contextPanel(page);
  await panel.getByRole("button", { name: ru["conversations.addLink"], exact: true }).click();
  const deal = await action("inbox.create-deal", `inbox/conversations/${conversation.id}/create-deal`, () => page.getByRole("dialog").getByRole("button", { name: ru["conversations.createDeal"], exact: true }).click());
  expect(await s.read(`deals/${deal.id}`)).toMatchObject({ client: client.id, lead: lead.id, business: s.business });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: ru["conversations.dialogActions"], exact: true }).click();
  await page.getByRole("menuitem", { name: ru["conversations.createTask"], exact: true }).click();
  const taskForm = page.getByRole("dialog", { name: ru["conversations.createTaskTitle"], exact: true });
  await taskForm.getByLabel(ru["taskWorkspace.name"], { exact: true }).fill(`${marker} callback`);
  await taskForm.getByLabel(ru["tasks.dueAt"], { exact: true }).fill(`${day}T10:30`);
  await page.screenshot({ path: info.outputPath("r01-inbox-task.png"), fullPage: true });
  const task: Task = await action("inbox.create-task", `inbox/conversations/${conversation.id}/create-task`, () => taskForm.getByRole("button", { name: ru["tasks.create"], exact: true }).click());
  expect(await s.read(`tasks/${task.id}`)).toMatchObject({ client: client.id, lead: lead.id, deal: deal.id, due_at: `${day}T05:30:00Z` });

  panel = await contextPanel(page);
  await panel.getByRole("button", { name: ru["conversations.bookClient"], exact: true }).click();
  const booking = page.getByTestId("appointment-form");
  await expect(booking).toBeVisible();
  await choose(page, booking, ru["branches.branch"], `${branch.name} · Abay 25`);
  await booking.getByLabel(ru["appointment.date"], { exact: true }).fill(day);
  await choose(page, booking, ru["appointment.service"], `${service.name} · 30 ${ru["appointment.minutes"]}`);
  await choose(page, booking, ru["appointment.resource"], staff.name);
  await choose(page, booking, ru["appointment.slot"], "09:00");
  const visit: Appointment = await action("calendar.book", "appointments", () => booking.getByTestId("appointment-submit").click());
  expect(await s.read(`appointments/${visit.id}`)).toMatchObject({ client: client.id, branch: branch.id, resource: staff.id, booked_price: "1250.50" });
  await page.goto(`/app/deals/${deal.id}`);
  await action("deal.win", `deals/${deal.id}/mark-won`, async () => {
    await page.locator('[data-crm-action-id="won"]').click();
    await page.getByRole("dialog").getByRole("button", { name: ru["actions.confirm"], exact: true }).click();
  });
  // Linked lifecycles do not close each other.
  expect((await s.read(`tasks/${task.id}`)).status).toBe(task.status);
  expect((await s.read(`appointments/${visit.id}`)).status).toBe("created");
  expect((await s.read(`leads/${lead.id}`)).status).toBe("contacted");
  await page.goto(`/app/tasks/${task.id}`);
  await action("task.complete", `tasks/${task.id}/complete`, () => page.getByRole("button", { name: ru["taskWorkspace.complete"], exact: true }).click());
  expect((await s.read(`tasks/${task.id}`)).status).toBe("done");
  await page.goto(`/app/calendar?date=${day}&branch=${branch.id}&appointment=${visit.id}`);
  await action("visit.confirm", `appointments/${visit.id}/confirm`, () => page.getByTestId("calendar-appointment-status-confirmed").click());
  await action("visit.complete", `appointments/${visit.id}/complete`, () => page.getByTestId("calendar-appointment-status-completed").click());
  expect(await s.read(`appointments/${visit.id}`)).toMatchObject({ status: "completed", client: client.id, branch: branch.id });

  await page.goto(`/app/clients/${client.id}`);
  await page.getByTestId("client-payments-open").click();
  await page.getByTestId("payment-add").click();
  const payment = page.getByTestId("payment-form");
  await choose(page, payment, ru["payments.link"], ru["payments.appointment"]);
  await payment.getByRole("button", { name: `${ru["payments.appointment"]}: ${ru["common.select"]}`, exact: true }).click();
  await payment.getByRole("list", { name: ru["payments.appointment"], exact: true }).getByRole("button").filter({ hasText: `#${visit.id}` }).click();
  await payment.getByLabel(new RegExp("^" + ru["payments.amount"] + " ")).fill("0");
  await payment.locator('button[type="submit"]').click();
  await expect(payment.getByText(ru["payments.amountInvalid"], { exact: true })).toBeVisible();
  await payment.getByLabel(new RegExp("^" + ru["payments.amount"] + " ")).fill("1250.50");
  const receipt = await action("payment.receipt", "client-payments", () => payment.locator('button[type="submit"]').click());
  await expect(page.getByTestId(`payment-row-${receipt.id}`)).toBeVisible();
  expect(await s.read(`client-payments/${receipt.id}`, { business: s.business })).toMatchObject({ client: client.id, link: { kind: "appointment", id: visit.id }, amount: "1250.50", kind: "receipt" });
  await page.reload();
  await page.getByRole("button", { name: ru["clients.archiveAction"], exact: true }).click();
  const archive = page.getByRole("dialog");
  await archive.locator("textarea").fill("Attempt while lead/conversation remain open");
  const rejected = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith(`/clients/${client.id}/archive/`));
  await archive.getByRole("button").last().click();
  expect((await rejected).status()).toBe(409);
  expect((await s.read(`clients/${client.id}`)).is_archived).toBe(false);
  expect((await s.read(`deals/${deal.id}`)).status).toBe("won");
  expect((await s.read(`appointments/${visit.id}`)).status).toBe("completed");

  const events = await s.read("activity-events", { business: s.business, entity_type: "Appointment", entity_id: visit.id });
  const completed = events.results.filter((event: { event_type: string }) => event.event_type === "appointment_completed");
  expect(completed).toHaveLength(1);
  expect(completed[0].actor).toBe(s.userId);
  expect(Number.isFinite(Date.parse(completed[0].created_at))).toBe(true);
  await page.goto("/app/timeline");
  const searched = page.waitForResponse(r => r.request().method() === "GET" && new URL(r.url()).pathname === "/api/activity-events/" && new URL(r.url()).searchParams.get("q") === marker);
  await page.getByRole("searchbox", { name: ru["timeline.search"], exact: true }).fill(marker);
  expect((await searched).ok()).toBeTruthy();
  await expect(page.getByTestId("timeline-workspace").locator('[aria-busy="true"]')).toHaveCount(0);
  await page.getByTestId(`timeline-event-${completed[0].id}`).filter({ visible: true }).first().click();
  const details = page.getByTestId("timeline-details");
  await expect(details).toContainText(marker);
  await details.locator(`a[href="/app/calendar/${visit.id}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/app/calendar/${visit.id}$`));
  await expect(page.getByText(service.name, { exact: true }).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("r01-completed-visit.png"), fullPage: true });
  // A separate customer without unfinished work demonstrates the positive archive/restore boundary.
  await page.goto("/app/clients");
  await page.getByTestId("page-primary-action").filter({ visible: true }).click();
  const clientForm = page.getByTestId("client-action-form");
  await clientForm.locator('input[name="full_name"]').fill(`${marker} finished`);
  const finished = await action("client.create", "clients", () => clientForm.getByTestId("client-action-submit").click());
  await page.goto(`/app/clients/${finished.id}`);
  await page.getByRole("button", { name: ru["clients.archiveAction"], exact: true }).click();
  const archiveFinished = page.getByRole("dialog");
  await archiveFinished.locator("textarea").fill("No unfinished work");
  await action("client.archive", `clients/${finished.id}/archive`, () => archiveFinished.getByRole("button", { name: ru["clients.archiveAction"], exact: true }).click());
  await action("client.restore", `clients/${finished.id}/restore`, () => page.getByRole("button", { name: /^(Отменить|Undo|Болдырмау)$/ }).click());
  expect((await s.read(`clients/${finished.id}`)).is_archived).toBe(false);
  await info.attach("R01 semantic receipts", { body: JSON.stringify({ business: s.business, actor: s.userId, client: client.id, lead: lead.id, deal: deal.id, task: task.id, appointment: visit.id, receipt: receipt.id, controls: receipts }, null, 2), contentType: "application/json" });
});
