import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";
import type { InboxContext, InboxConversation } from "../src/api/inbox";

test.use({ actionTimeout: 15_000 });

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

async function openContext(page: Page, label = ru["conversations.aboutClient"]) {
  const trigger = page.getByRole("button", { name: label, exact: true });
  await expect(trigger).toBeVisible();
  const panel = page.getByTestId("inbox-customer-context").filter({ visible: true });
  if (await trigger.getAttribute("aria-expanded") !== "true") await trigger.click();
  await expect(panel).toBeVisible();
  return panel;
}

test("real client, appointment, lead and deal links preserve the unsent reply", async ({ page }, info) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const client = await session.create<{ id: number }>("clients", { full_name: "Inspector customer", notes: "Call in the afternoon", phone: "+77001234567" });
  await session.action(`inbox/conversations/${conversation.id}/link-client`, { client_id: client.id });
  await session.action(`inbox/conversations/${conversation.id}/create-deal`, { title: "Inspector consultation" });
  const resource = await session.create<{ id: number }>("resources", { name: "Inspector specialist", weekly_schedule: Array.from({ length: 7 }, (_, weekday) => ({ weekday, start_time: "09:00", end_time: "20:00", is_day_off: false })) });
  const service = await session.create<{ id: number }>("services", { name: "Inspector appointment", duration_minutes: 30, price_from: 100 });
  const date = new Date(Date.now() + 4 * 86400_000).toISOString().slice(0, 10);
  const slots = await session.read("appointments/available-slots", { business_id: session.business, service_id: service.id, resource_id: resource.id, date });
  expect(slots.length).toBeGreaterThan(1);
  for (const slot of slots.slice(0, 2)) await session.create("appointments", { client: client.id, service: service.id, resource: resource.id, start_at: slot.start_at });
  const context: InboxContext = await session.read(`inbox/conversations/${conversation.id}/context`);
  expect(context.appointments.items).toHaveLength(2);
  await page.goto(`/app/conversations/${conversation.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await composer.fill("Unsent reply  ");
  let panel = await openContext(page);
  await expect(panel.getByText("Call in the afternoon", { exact: true })).toBeVisible();
  await expect(panel.getByRole("heading", { name: ru["conversations.clientUpcomingAppointments"] })).toBeVisible();
  await expect(panel.getByText("Inspector specialist", { exact: true })).toHaveCount(2);
  const appointmentLink = panel.locator(`a[href="${context.appointments.items[0].href}"]`);
  expect((await appointmentLink.boundingBox())!.y).toBeLessThan((await panel.locator(`a[href="${context.deal.data!.href}"]`).boundingBox())!.y);
  await page.screenshot({ path: info.outputPath("inspector-linked.png"), fullPage: true });
  for (const href of [context.client.data!.href, context.appointments.items[0].href, context.deal.data!.href, context.lead.data!.href]) {
    panel = await openContext(page);
    await panel.locator(`a[href="${href}"]`).click();
    await expect(page).toHaveURL(new RegExp(`${href.replaceAll("?", "\\?")}$`));
    await expect(page.getByText("Unexpected Application Error")).toHaveCount(0);
    await page.goBack();
    await expect(composer).toHaveValue("Unsent reply  ");
  }
  for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.reload();
    panel = await openContext(page, copy["conversations.aboutClient"]);
    await expect(panel.getByRole("heading", { name: copy["conversations.aboutClient"], exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`inspector-${locale}.png`), fullPage: true });
    if (info.project.name === "mobile-chromium") {
      await page.keyboard.press("Escape");
      await expect(page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true })).toBeFocused();
    }
  }
});

test("context errors recover locally and denied children show no leaked identities", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const original: InboxContext = await session.read(`inbox/conversations/${conversation.id}/context`);
  let state: "failure" | "denied" | "normal" = "failure";
  await page.route(`**/api/inbox/conversations/${conversation.id}/context/`, route => {
    if (state === "failure") return route.fulfill({ status: 503, json: { detail: "Unavailable" } });
    if (state === "normal") return route.fulfill({ json: original });
    return route.fulfill({ json: { ...original, client: { state: "forbidden", data: null }, lead: { state: "forbidden", data: null }, deal: { state: "forbidden", data: null }, appointments: { ...original.appointments, state: "forbidden", items: [] }, task: null, actions: { update: false } } });
  });
  await page.goto(`/app/conversations/${conversation.id}`);
  let panel = await openContext(page);
  await expect(panel.getByText(ru["conversations.contextLoadError"], { exact: true })).toBeVisible();
  state = "normal";
  await panel.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(panel.locator(`a[href="${original.client.data!.href}"]`)).toBeVisible();
  state = "denied";
  await page.reload();
  panel = await openContext(page);
  await expect(panel.getByTestId("inbox-context-client-forbidden")).toBeVisible();
  await expect(panel.locator("a")).toHaveCount(0);
  await expect(panel.getByRole("button", { name: ru["conversations.addLink"], exact: true })).toHaveCount(0);
  await panel.getByRole("button", { name: ru["conversations.closeContext"] }).click();
  await expect(page.getByTestId("inbox-action-send")).toBeDisabled();
});

test("AI inserts an editable draft and delivery retry uses the failed message and same uncertain request key", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  let sends = 0;
  let retries: Array<{ id: number; key: string | undefined }> = [];
  const message = { id: 91001, conversation: conversation.id, direction: "outbound", sender_type: "manager", text: "Failed synthetic delivery", status: "failed", created_at: new Date().toISOString(), payload_json: {}, error_text: "secret-provider-token", delivery_attempts: 1, attachments: [] };
  await page.route(`**/api/inbox/conversations/${conversation.id}/messages/**`, route => {
    if (route.request().method() === "POST") { sends++; return route.fulfill({ json: { ...message, status: "sent" } }); }
    return route.fulfill({ json: { count: 2, results: [message, { ...message, id: 91002, status: "sent", text: "Later successful delivery" }], next: null, previous: null, has_more: false } });
  });
  await page.route(`**/api/inbox/conversations/${conversation.id}/suggest-reply/`, route => route.fulfill({ json: { suggested_reply: "Suggested answer" } }));
  await page.route(`**/api/inbox/conversations/${conversation.id}/retry-message/`, route => {
    retries.push({ id: route.request().postDataJSON().message_id, key: route.request().headers()["idempotency-key"] });
    return route.fulfill({ status: 503, json: { detail: "Temporary delivery failure" } });
  });
  await page.goto(`/app/conversations/${conversation.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await composer.fill("Existing draft  ");
  await page.getByRole("button", { name: ru["conversations.prepareReply"], exact: true }).click();
  await page.getByRole("button", { name: ru["conversations.useSuggestedReply"], exact: true }).click();
  await expect(composer).toHaveValue("Existing draft  \nSuggested answer");
  expect(sends).toBe(0);
  await composer.fill("Edited response");
  const failed = page.locator('[data-message-id="91001"]');
  await expect(failed.getByTestId("message-delivery-retry")).toBeVisible();
  await expect(page.locator('[data-message-id="91002"]').getByTestId("message-delivery-retry")).toHaveCount(0);
  await expect(page.getByText("secret-provider-token", { exact: true })).toHaveCount(0);
  await failed.getByTestId("message-delivery-retry").click();
  await expect(failed.getByTestId("message-delivery-retry")).toBeEnabled();
  await failed.getByTestId("message-delivery-retry").click();
  await expect.poll(() => retries.length).toBe(2);
  expect(retries[0].id).toBe(91001);
  expect(retries[0].key).toBeTruthy();
  expect(retries[1]).toEqual(retries[0]);
  await expect(composer).toHaveValue("Edited response");
});

test("booking shortcut preselects the client and link search recovers without losing the draft", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const customer = await session.create<{ id: number }>("clients", { full_name: "Booking shortcut customer" });
  await session.action(`inbox/conversations/${conversation.id}/link-client`, { client_id: customer.id });
  await page.goto(`/app/conversations/${conversation.id}`);
  await page.getByTestId("inbox-action-composer").fill("Book after confirming");
  let panel = await openContext(page);
  await panel.getByRole("button", { name: ru["conversations.bookClient"], exact: true }).click();
  await expect(page).toHaveURL(/\/app\/calendar/);
  await expect(page.getByRole("dialog").getByRole("combobox", { name: /^Клиент / })).toContainText("Booking shortcut customer");
  await page.goBack();
  await expect(page.getByTestId("inbox-action-composer")).toHaveValue("Book after confirming");
  panel = await openContext(page);
  let fail = true;
  await page.route(`**/api/inbox/conversations/${conversation.id}/link-candidates/**`, route => fail
    ? route.fulfill({ status: 503, json: { detail: "Search unavailable" } }) : route.continue());
  await panel.getByRole("button", { name: ru["conversations.contextActions"], exact: true }).click();
  await page.getByRole("menuitem", { name: ru["conversations.changeLink.client"], exact: true }).focus();
  await page.keyboard.press("Escape");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("button", { name: ru["conversations.contextActions"], exact: true })).toBeFocused();
  await panel.getByRole("button", { name: ru["conversations.contextActions"], exact: true }).click();
  await page.getByRole("menuitem", { name: ru["conversations.changeLink.client"], exact: true }).click();
  const dialog = page.getByRole("dialog", { name: ru["conversations.linkClientTitle"], exact: true });
  await expect(dialog.getByText(ru["conversations.noLinkCandidates"], { exact: true })).toHaveCount(0);
  fail = false;
  await dialog.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await dialog.getByPlaceholder(ru["conversations.linkSearchPlaceholder"]).fill("Booking shortcut customer");
  await expect(dialog.getByRole("button", { name: "Booking shortcut customer", exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Booking shortcut customer", exact: true }).click();
  await expect(dialog).not.toBeVisible();
});

test("CRM menu opens preview and requires granular confirmation before execution", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const qualification = { summary: "Synthetic CRM proposal", intent: "appointment_request", confidence: .9, should_create_lead: false, should_create_deal: true, should_create_task: true };
  const previewId = new Date().toISOString();
  let previewed = false;
  const executions: Record<string, unknown>[] = [];
  const decorate = (item: InboxConversation) => item.id === conversation.id && previewed ? { ...item, metadata_json: { ...item.metadata_json, conversation_qualification_preview: { qualification, qualified_at: previewId } } } : item;
  await page.route(/\/api\/inbox\/conversations\/(?:\?.*)?$/, async route => {
    const response = await route.fetch(); const data = await response.json();
    await route.fulfill({ json: { ...data, results: data.results.map(decorate) } });
  });
  await page.route(`**/api/inbox/conversations/${conversation.id}/`, async route => {
    const response = await route.fetch(); await route.fulfill({ json: decorate(await response.json()) });
  });
  await page.route(`**/api/inbox/conversations/${conversation.id}/qualify/`, route => {
    previewed = true; return route.fulfill({ json: { qualification, conversation: decorate(conversation) } });
  });
  await page.route(`**/api/inbox/conversations/${conversation.id}/run-pipeline/`, route => {
    executions.push(route.request().postDataJSON());
    return route.fulfill({ json: { conversation, created: { client: false, lead: false, deal: false, task: true }, qualification: null } });
  });
  await page.goto(`/app/conversations/${conversation.id}`);
  await expect(page.getByRole("button", { name: ru["conversations.previewQualification"], exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: ru["conversations.dialogActions"], exact: true }).click();
  await page.getByRole("menuitem", { name: ru["conversations.crmAutomation"], exact: true }).click();
  const preview = page.getByRole("dialog", { name: ru["conversations.crmAutomation"], exact: true });
  await preview.getByRole("button", { name: ru["conversations.previewQualification"], exact: true }).click();
  await expect(preview.getByText(qualification.summary, { exact: true })).toBeVisible();
  await preview.getByRole("button", { name: ru["conversations.confirmPipelineTitle"], exact: true }).click();
  const confirmation = page.getByRole("dialog", { name: ru["conversations.confirmPipelineTitle"], exact: true });
  expect(executions).toHaveLength(0);
  await confirmation.getByRole("checkbox", { name: ru["conversations.confirmPipeline.create_deal"] }).uncheck();
  await confirmation.getByRole("button", { name: ru["conversations.confirmPipelineSubmit"], exact: true }).click();
  await expect.poll(() => executions.length).toBe(1);
  expect(executions[0]).toMatchObject({ confirmed_actions: ["create_task"], create_lead: false, create_deal: false, create_task: true, preview_id: previewId, apply_ai_decisions: false });
  await expect(confirmation).not.toBeVisible();
  await page.unrouteAll({ behavior: "wait" });
});

test("switching conversations preserves each draft and a late send cannot clear another draft", async ({ page }, info) => {
  const session = await crmSession(page);
  const original = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const context = await session.read(`inbox/conversations/${original.id}/context`);
  const otherId = 92001;
  const first = { ...original, client_name: "Draft Alpha", unread_count: 0 };
  const second = { ...first, id: otherId, client_name: "Draft Beta" };
  const values = [first, second];
  await page.evaluate(({ business, conversation }) => sessionStorage.setItem(`zani_inbox_draft:${business}:${conversation}`, "Legacy unsent draft"), { business: original.business, conversation: original.id });
  await page.route(/\/api\/inbox\/conversations\/(?:\?.*)?$/, route => route.fulfill({ json: { count: 2, results: values, next: null, previous: null } }));
  for (const item of values) {
    await page.route(`**/api/inbox/conversations/${item.id}/`, route => route.fulfill({ json: item }));
    await page.route(`**/api/inbox/conversations/${item.id}/context/`, route => route.fulfill({ json: { ...context, conversation_id: item.id } }));
    await page.route(`**/api/inbox/conversations/${item.id}/messages/**`, route => route.fulfill({ json: { count: 0, results: [], next: null, previous: null } }));
  }
  let release: (() => void) | undefined;
  let started = false;
  await page.route(`**/api/inbox/conversations/${first.id}/messages/`, async route => {
    if (route.request().method() !== "POST") return route.fallback();
    started = true;
    await new Promise<void>(resolve => { release = resolve; });
    await route.fulfill({ json: { id: 92003, conversation: first.id, text: "Alpha draft", status: "sent" } });
  });
  await page.goto(`/app/conversations/${first.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  async function select(name: string) {
    if (info.project.name === "mobile-chromium") await page.getByRole("button", { name: ru["common.close"], exact: true }).first().click();
    await page.getByRole("button").filter({ has: page.getByText(name, { exact: true }) }).click();
  }
  await expect(composer).toHaveValue("Legacy unsent draft");
  await composer.fill("Alpha draft");
  await select("Draft Beta");
  await expect(composer).toHaveValue("");
  await composer.fill("Beta draft");
  await select("Draft Alpha");
  await expect(composer).toHaveValue("Alpha draft");
  await page.getByTestId("inbox-action-send").click();
  await expect.poll(() => started).toBe(true);
  await select("Draft Beta");
  await expect(composer).toHaveValue("Beta draft");
  release!();
  await expect(composer).toBeEnabled();
  await expect(composer).toHaveValue("Beta draft");
  await select("Draft Alpha");
  await expect(composer).toHaveValue("");
});

test("unlinked inspector offers one client action and links a scoped existing customer", async ({ page }) => {
  const session = await crmSession(page);
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const context: InboxContext = await session.read(`inbox/conversations/${conversation.id}/context`);
  const client = await session.create<{ id: number }>("clients", { full_name: "Selected existing client" });
  let linked = false;
  await page.route(`**/api/inbox/conversations/${conversation.id}/context/`, route => linked ? route.continue() : route.fulfill({ json: {
    ...context, client: { state: "empty", data: null }, lead: { state: "empty", data: null }, deal: { state: "empty", data: null }, task: null,
    appointments: { state: "empty", kind: "client", items: [], has_more: false },
    actions: { ...context.actions, link_client: true, create_client: true, link_lead: true, create_lead: true, link_deal: true, create_deal: true, book: false },
  } }));
  await page.goto(`/app/conversations/${conversation.id}`);
  const panel = await openContext(page);
  await expect(panel.getByRole("button", { name: ru["conversations.linkClientAction"], exact: true })).toHaveCount(1);
  await expect(panel.getByRole("button", { name: ru["conversations.createClient"], exact: true })).toHaveCount(0);
  await expect(panel.getByRole("button", { name: ru["conversations.addLink"], exact: true })).toBeVisible();
  await expect(panel.locator("a")).toHaveCount(0);
  await panel.getByRole("button", { name: ru["conversations.linkClientAction"], exact: true }).click();
  const dialog = page.getByRole("dialog", { name: ru["conversations.linkClientTitle"], exact: true });
  await expect(dialog.getByRole("button", { name: ru["conversations.createClient"], exact: true })).toBeVisible();
  await dialog.getByPlaceholder(ru["conversations.linkSearchPlaceholder"]).fill("Selected existing client");
  linked = true;
  await dialog.getByRole("button", { name: "Selected existing client", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(panel.locator(`a[href="/app/clients/${client.id}"]`)).toBeVisible();
  expect((await session.read(`inbox/conversations/${conversation.id}/context`)).client.data.id).toBe(client.id);
});
