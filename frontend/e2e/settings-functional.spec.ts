import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";
import type { AppointmentMessageSetting, BusinessRole, CustomFieldDefinition } from "../src/types";
import type { InboxConversation } from "../src/api/inbox";

test.use({ actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

async function open(page: Page, section: string) {
  await page.goto(`/app/settings#${section}`);
  await expect(page.getByTestId("settings-workspace-ready")).toBeVisible();
  await expect(page.locator(`#${section}`)).toBeVisible();
  await expect(page.locator(`#${section} .platforma-loading`)).toHaveCount(0, { timeout: 20_000 });
  return page.locator(`#${section}`);
}

for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`ten sections use scoped real data and localized states (${language})`, async ({ page }, info) => {
    const session = await crmSession(page);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    const selectedRequests: string[] = [];
    page.on("request", request => {
      if (request.method() === "GET" && /\/api\/(custom-fields|quick-replies|notification-preferences|billing\/(current-subscription|entitlements))\//.test(request.url())) selectedRequests.push(request.url());
    });
    for (const section of ["business-profile", "team-access", "roles", "security-center", "appointment-messages", "notification-preferences", "quick-replies", "billing", "usage", "custom-fields"]) {
      const panel = await open(page, section);
      await expect(panel.locator('[role="alert"]')).toHaveCount(0);
      await expect(panel.locator("p,button,label,legend,h2").filter({ hasText: /^(settings|businessForm)\.[a-z]/ })).toHaveCount(0);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBe(true);
      if (["business-profile", "appointment-messages", "usage", "custom-fields"].includes(section)) await page.screenshot({ path: info.outputPath(`${section}-${language}.png`), fullPage: true });
    }
    expect(new Set(selectedRequests.map(url => new URL(url).pathname)).size).toBe(5);
    for (const url of selectedRequests) expect(new URL(url).searchParams.get("business")).toBe(String(session.business));
    const panel = await open(page, "business-profile");
    await panel.getByRole("button", { name: copy["businessForm.group.appearance"], exact: true }).click();
    await expect(panel.getByLabel(copy["businessForm.brandColor"], { exact: true })).toHaveAttribute("readonly", "");
    await expect(panel.getByLabel(copy["businessForm.brandLogoUrl"], { exact: true })).toHaveAttribute("readonly", "");
  });
}

test("business values save while reference metadata is preserved; invalid timezone recovers", async ({ page }) => {
  const session = await crmSession(page);
  const before = await session.read(`businesses/${session.business}`);
  const panel = await open(page, "business-profile");
  await panel.getByLabel(ru["businessForm.city"], { exact: true }).fill("Settings city");
  await panel.getByRole("button", { name: ru["businessForm.group.appointments"], exact: true }).click();
  await expect(panel.getByLabel(ru["businessForm.bookingBufferMinutes"], { exact: true })).toHaveAttribute("readonly", "");
  await panel.getByLabel(ru["businessForm.timezone"], { exact: true }).fill("Invalid/TimeZone");
  await panel.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  expect((await session.read(`businesses/${session.business}`)).city).toBe(before.city);
  await panel.getByLabel(ru["businessForm.timezone"], { exact: true }).fill("Asia/Almaty");
  await panel.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`businesses/${session.business}`)).city).toBe("Settings city");
  const after = await session.read(`businesses/${session.business}`);
  for (const key of ["language", "sla_minutes", "booking_buffer_minutes", "cancellation_policy", "prepayment_policy", "brand_color", "brand_logo_url"]) expect(after[key]).toEqual(before[key]);
});

test("appointment edits preserve another card draft and recover from a rejected save", async ({ page }) => {
  const session = await crmSession(page);
  const settings = await session.list<AppointmentMessageSetting>("appointment-message-settings");
  const panel = await open(page, "appointment-messages");
  const texts = panel.locator("textarea");
  await expect(texts).toHaveCount(3);
  await texts.nth(0).fill("Changed {client_name}");
  await texts.nth(1).fill("Keep other draft {time}");
  const firstCard = texts.nth(0).locator('xpath=ancestor::div[contains(@class,"flex-col")][1]');
  await firstCard.getByRole("combobox").click();
  await expect(page.getByRole("option", { name: "SMS", exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await firstCard.getByRole("button", { name: ru["settings.enabled"], exact: true }).click();
  await expect(texts.nth(0)).toHaveValue("Changed {client_name}");
  await expect(texts.nth(1)).toHaveValue("Keep other draft {time}");
  await page.route("**/api/appointment-message-settings/*/", route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { detail: "Try again" } }) : route.continue(), { times: 1 });
  await firstCard.getByRole("button", { name: ru["settings.appointmentMessages.saveScenario"], exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(texts.nth(0)).toHaveValue("Changed {client_name}");
  await firstCard.getByRole("button", { name: ru["settings.appointmentMessages.saveScenario"], exact: true }).click();
  await expect.poll(async () => (await session.list<AppointmentMessageSetting>("appointment-message-settings")).some(row => row.template_text === "Changed {client_name}")).toBe(true);
  await expect(texts.nth(1)).toHaveValue("Keep other draft {time}");
  expect(settings).toHaveLength(3);
});

test("personal preferences load failure recovers and toggle persists for selected business", async ({ page }) => {
  const session = await crmSession(page);
  let fail = true;
  await page.route("**/api/notification-preferences/**", route => fail && route.request().method() === "GET" ? route.fulfill({ status: 503, json: { detail: "Unavailable" } }) : route.continue());
  const panel = await open(page, "notification-preferences");
  await expect(panel.getByRole("alert")).toBeVisible({ timeout: 20_000 });
  await expect(panel.getByRole("button", { name: ru["settings.enabled"], exact: true })).toHaveCount(0);
  fail = false;
  await panel.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await panel.getByRole("button", { name: ru["settings.enabled"], exact: true }).first().click();
  await expect(panel.getByRole("button", { name: ru["settings.disabled"], exact: true })).toBeVisible();
  const result = await session.read("notification-preferences", { business: session.business, user: "me" });
  expect(result.results.some((row: { business: number; in_app_enabled: boolean }) => row.business === session.business && !row.in_app_enabled)).toBe(true);
});

test("custom definition created in settings reaches typed card fields and retains values on deactivate", async ({ page }, info) => {
  const session = await crmSession(page);
  const suffix = String(Date.now());
  const panel = await open(page, "custom-fields");
  const create = panel.locator("form").first();
  const label = `Проверка ${suffix}`;
  await create.getByLabel(ru["settings.templateTitle"], { exact: true }).fill(label);
  await create.getByRole("group", { name: ru["settings.editRoles"], exact: true }).getByLabel(ru["settings.role.operator"], { exact: true }).check();
  await create.getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(panel.getByText(label, { exact: true })).toBeVisible();
  const definition = (await session.list<CustomFieldDefinition>("custom-fields")).find(row => row.label === label)!;
  expect(definition.key).toMatch(/^[a-zA-Z0-9_-]+$/);
  expect(definition.permissions_json.edit_roles).toEqual(["operator"]);
  const multi = await session.create<CustomFieldDefinition>("custom-fields", { entity_type: "client", key: `choices_${suffix}`, label: "Card choices", field_type: "multiselect", options_json: { options: [{ value: "a", label: "Alpha" }, "b"] } });
  const boolean = await session.create<CustomFieldDefinition>("custom-fields", { entity_type: "client", key: `boolean_${suffix}`, label: "Card boolean", field_type: "boolean" });
  const customer = await session.create<{ id: number }>("clients", { full_name: `Fields ${suffix}` });
  await page.goto(`/app/clients?client=${customer.id}&tab=notes`);
  const drawer = page.getByRole("dialog");
  await drawer.getByRole("button", { name: ru["crmCard.overview"], exact: true }).click();
  await drawer.getByLabel(label, { exact: true }).fill("Saved from card");
  await drawer.getByRole("group", { name: multi.label, exact: true }).getByLabel("Alpha", { exact: true }).check();
  const save = drawer.getByRole("button", { name: ru["crmCard.saveFields"], exact: true });
  await page.route("**/api/custom-field-values/bulk-upsert/", route => route.fulfill({ status: 503, json: { detail: "Retry values" } }), { times: 1 });
  await save.click();
  await expect(drawer.getByRole("alert")).toBeVisible();
  await expect(drawer.getByLabel(label, { exact: true })).toHaveValue("Saved from card");
  await save.click();
  await expect(save).toBeDisabled();
  const values = await session.read("custom-field-values", { business: session.business, entity_type: "client", entity_id: String(customer.id) });
  expect(values.results.find((row: { definition: number }) => row.definition === multi.id).value_json.value).toEqual(["a"]);
  expect(values.results.find((row: { definition: number }) => row.definition === boolean.id)).toBeUndefined();
  await page.screenshot({ path: info.outputPath("custom-fields-card.png"), fullPage: true });
  const settingsPanel = await open(page, "custom-fields");
  const card = settingsPanel.getByText(label, { exact: true }).locator('xpath=ancestor::div[contains(@class,"rounded-card")][1]');
  await card.getByRole("button", { name: ru["settings.disable"], exact: true }).click();
  await expect.poll(async () => (await session.read(`custom-fields/${definition.id}`)).is_active).toBe(false);
  expect((await session.read("custom-field-values", { business: session.business, definition: definition.id })).results[0].value_json.value).toBe("Saved from card");
  const optionCard = settingsPanel.getByText(multi.label, { exact: true }).locator('xpath=ancestor::div[contains(@class,"rounded-card")][1]');
  await optionCard.getByRole("button", { name: ru["settings.edit"], exact: true }).click();
  const edit = settingsPanel.locator("form").nth(1);
  await edit.getByLabel(ru["settings.templateTitle"], { exact: true }).fill("Renamed choices");
  await expect(edit.getByLabel(ru["settings.customFieldRequiredMetadata"], { exact: true })).toBeDisabled();
  await edit.getByRole("button", { name: ru["settings.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`custom-fields/${multi.id}`)).label).toBe("Renamed choices");
  expect((await session.read(`custom-fields/${multi.id}`)).options_json).toEqual(multi.options_json);
});

test("billing saves separate requisites and usage renders real periods and units", async ({ page }) => {
  const session = await crmSession(page);
  const business = await session.read(`businesses/${session.business}`);
  const panel = await open(page, "billing");
  await panel.getByLabel(ru["settings.billingEmail"], { exact: true }).fill("billing-settings@example.test");
  await panel.getByLabel(ru["settings.invoiceName"], { exact: true }).fill("Subscription payer");
  await panel.getByRole("button", { name: ru["settings.saveBilling"], exact: true }).click();
  await expect.poll(async () => (await session.read("billing/current-subscription", { business: session.business })).billing_email).toBe("billing-settings@example.test");
  expect((await session.read(`businesses/${session.business}`)).invoice_email).toBe(business.invoice_email);
  await expect(panel.getByLabel(ru["settings.paymentMethodReference"], { exact: true })).toHaveAttribute("readonly", "");
  await expect(panel.getByRole("button", { name: ru["settings.pauseSubscription"], exact: true })).toHaveCount(0);
  const subscription = await session.read("billing/current-subscription", { business: session.business });
  const plans = await session.list<{ id: number; name: string }>("billing/plans");
  const alternative = plans.find(plan => plan.id !== subscription.plan?.id && plan.id !== subscription.requested_plan)!;
  expect(alternative).toBeTruthy();
  await panel.getByRole("combobox", { name: new RegExp(ru["settings.newPlan"]) }).click();
  await page.getByRole("option", { name: alternative.name, exact: true }).click();
  await panel.getByRole("button", { name: ru["settings.savePlanPreference"], exact: true }).click();
  await expect.poll(async () => (await session.read("billing/current-subscription", { business: session.business })).requested_plan).toBe(alternative.id);
  expect((await session.read("billing/current-subscription", { business: session.business })).plan).toEqual(subscription.plan);
  const usage = await open(page, "usage");
  await expect(usage).toContainText(ru["settings.usageCurrent"]);
  await expect(usage).toContainText("МиБ");
});

test("role visibility saves one atomic scope change without granting actions", async ({ page }) => {
  const session = await crmSession(page);
  const roles = await session.list<BusinessRole>("team/roles");
  const role = roles.find(row => row.preset_key === "operator")!;
  const before = role.permissions.filter(permission => permission.resource === "clients");
  const panel = await open(page, "roles");
  await panel.getByRole("button").filter({ hasText: role.name }).first().click();
  await panel.getByRole("button", { name: ru["settings.openAdvanced"], exact: true }).click();
  const group = panel.getByText(ru["settings.accessGroup.clients"], { exact: true }).locator('xpath=ancestor::div[contains(@class,"rounded-card")][1]');
  const requests: unknown[] = [];
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith(`/team/roles/${role.id}/visibility/`)) requests.push(request.postDataJSON()); });
  await group.getByRole("button", { name: ru["settings.visibility.business"], exact: true }).click();
  await expect.poll(async () => (await session.read(`team/roles/${role.id}`)).permissions.filter((row: { resource: string }) => row.resource === "clients").every((row: { scope: string }) => row.scope === "business")).toBe(true);
  expect(requests).toHaveLength(1);
  const after = (await session.read(`team/roles/${role.id}`)).permissions;
  for (const permission of before) expect(after.find((row: { id: number }) => row.id === permission.id).is_allowed).toBe(permission.is_allowed);
});

test("quick reply settings feed the Inbox draft without sending a message", async ({ page }) => {
  const session = await crmSession(page);
  const title = `Settings reply ${Date.now()}`;
  const text = "Prepared response from settings";
  const panel = await open(page, "quick-replies");
  const form = panel.locator("form").first();
  await form.getByLabel(ru["settings.templateTitle"], { exact: true }).fill(title);
  await form.getByLabel(ru["settings.templateText"], { exact: true }).fill(text);
  await form.getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(panel.getByText(title, { exact: true })).toBeVisible();
  const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
  const before = await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`);
  await page.goto(`/app/conversations/${conversation.id}`);
  await page.getByRole("button", { name: ru["conversations.quickRepliesButton"], exact: true }).click();
  await page.getByRole("button").filter({ hasText: title }).click();
  await expect(page.getByTestId("inbox-action-composer")).toHaveValue(text);
  expect((await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`)).map(row => row.id)).toEqual(before.map(row => row.id));
});

test("team invite, revoke, department and confirmed login toggle work without external delivery", async ({ page }) => {
  const session = await crmSession(page);
  const panel = await open(page, "team-access");
  const suffix = String(Date.now());
  await panel.getByLabel(ru["settings.loginEmail"], { exact: true }).fill(`settings-${suffix}@example.test`);
  await panel.getByLabel(ru["settings.fullName"], { exact: true }).fill(`Settings member ${suffix}`);
  await panel.getByRole("combobox", { name: new RegExp(ru["settings.delivery"]) }).click();
  await page.getByRole("option", { name: ru["settings.copyLink"], exact: true }).click();
  await panel.getByRole("button", { name: ru["settings.createInvite"], exact: true }).click();
  await expect(panel.getByText(ru["settings.inviteCreatedTitle"], { exact: true })).toBeVisible();
  const invitations = await session.list<{ id: number; email: string; role: string }>("team/invitations");
  const invitation = invitations.find(row => row.email === `settings-${suffix}@example.test`)!;
  expect(invitation.role).toBe("operator");
  const row = panel.getByText(`Settings member ${suffix}`, { exact: true }).locator('xpath=ancestor::div[contains(@class,"rounded-2xl")][1]');
  await row.getByRole("button", { name: ru["settings.revoke"], exact: true }).click();
  await expect.poll(async () => (await session.read(`team/invitations/${invitation.id}`)).status).toBe("revoked");
  const name = panel.getByPlaceholder(ru["settings.departmentPlaceholder"], { exact: true });
  await name.fill(`Settings department ${suffix}`);
  await name.locator("xpath=ancestor::form").getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(panel.getByText(`Settings department ${suffix}`, { exact: true })).toBeVisible();
  const members = await session.list<{ id: number; role: string; is_active: boolean; user: { full_name: string; email: string } }>("team/members");
  const member = members.find(item => item.role === "operator" && item.is_active)!;
  await panel.getByRole("combobox", { name: new RegExp(ru["settings.memberStep"]) }).click();
  await page.getByRole("option", { name: member.user.full_name || member.user.email, exact: true }).click();
  for (const enabled of [false, true]) {
    await panel.getByTestId("team-access-toggle").click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: ru[enabled ? "teamAccess.enable" : "teamAccess.disable"], exact: true }).click();
    await expect.poll(async () => (await session.read(`team/members/${member.id}`)).is_active).toBe(enabled);
  }
});
