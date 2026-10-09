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
  test(`settings sections use scoped real data and localized states (${language})`, async ({ page }, info) => {
    const session = await crmSession(page);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    const selectedRequests: string[] = [];
    page.on("request", request => {
      if (request.method() === "GET" && /\/api\/(custom-fields|quick-replies|notification-preferences|billing\/(current-subscription|entitlements))\//.test(request.url())) selectedRequests.push(request.url());
    });
    for (const section of ["business-profile", "team-access", "roles", "security-center", "appointment-messages", "quick-replies", "billing", "usage", "custom-fields"]) {
      const panel = await open(page, section);
      await expect(panel.locator('[role="alert"]')).toHaveCount(0);
      await expect(panel.locator("p,button,label,legend,h2").filter({ hasText: /^(settings|businessForm)\.[a-z]/ })).toHaveCount(0);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBe(true);
      await expect.poll(() => panel.locator('input:visible,textarea:visible,[role="combobox"]:visible').evaluateAll(controls => controls.filter(control => {
        const bounds = control.getBoundingClientRect();
        return bounds.width > 0 && (bounds.left < -1 || bounds.right > window.innerWidth + 1);
      }).map(control => control.getAttribute("name") || control.getAttribute("aria-label") || control.tagName))).toEqual([]);
      if (language === "ru" || ["business-profile", "appointment-messages", "usage", "custom-fields"].includes(section)) await page.screenshot({ path: info.outputPath(`${section}-${language}.png`), fullPage: true });
    }
    expect(new Set(selectedRequests.map(url => new URL(url).pathname)).size).toBe(3);
    for (const url of selectedRequests) expect(new URL(url).searchParams.get("business")).toBe(String(session.business));
    const panel = await open(page, "business-profile");
    await expect(panel.getByLabel(copy["businessForm.slug"], { exact: true })).toHaveCount(0);
    await expect(panel.getByRole("button", { name: copy["businessForm.group.appointments"], exact: true })).toHaveCount(0);
    await expect(panel.getByRole("button", { name: copy["businessForm.group.finance"], exact: true })).toHaveCount(0);
    await expect(panel.getByRole("button", { name: copy["businessForm.group.appearance"], exact: true })).toHaveCount(0);
    await expect(panel.getByText(copy["settings.redesign.reference"], { exact: true })).toHaveCount(0);
  });
}

test("business values save while reference metadata is preserved; invalid timezone recovers", async ({ page }) => {
  const session = await crmSession(page);
  const before = await session.read(`businesses/${session.business}`);
  const panel = await open(page, "business-profile");
  await panel.getByLabel(ru["businessForm.city"], { exact: true }).fill("Settings city");
  await panel.getByLabel(ru["businessForm.timezone"], { exact: true }).fill("Invalid/TimeZone");
  await panel.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  expect((await session.read(`businesses/${session.business}`)).city).toBe(before.city);
  await panel.locator('input[name="timezone"]').fill("Asia/Almaty");
  await panel.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`businesses/${session.business}`)).city).toBe("Settings city");
  const after = await session.read(`businesses/${session.business}`);
  for (const key of ["slug", "financial_source_mode", "financial_connector", "language", "sla_minutes", "booking_buffer_minutes", "cancellation_policy", "prepayment_policy", "brand_color", "brand_logo_url"]) expect(after[key]).toEqual(before[key]);
  await panel.locator('input[name="invoice_email"]').fill("invalid-email");
  await panel.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect(panel.locator('input[name="invoice_email"]')).toBeVisible();
  await expect(panel.locator('input[name="invoice_email"]')).toBeFocused();
  await expect(panel.getByRole("alert")).toHaveText(ru["settings.redesign.invalidEmail"]);
  expect((await session.read(`businesses/${session.business}`)).invoice_email).toBe(before.invoice_email);
});

test("appointment edits preserve another card draft and recover from a rejected save", async ({ page }) => {
  const session = await crmSession(page);
  const settings = await session.list<AppointmentMessageSetting>("appointment-message-settings");
  const panel = await open(page, "appointment-messages");
  const text = panel.locator("textarea");
  const scenarios = panel.locator("nav button");
  await expect(text).toHaveCount(1);
  await text.fill("Changed {client_name}");
  await scenarios.nth(1).click();
  await text.fill("Keep other draft {time}");
  await scenarios.nth(0).click();
  await panel.getByRole("combobox").click();
  await expect(page.getByRole("option", { name: "SMS", exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await panel.getByRole("switch").click();
  await expect(text).toHaveValue("Changed {client_name}");
  await expect(panel.getByRole("switch")).toBeEnabled();
  await page.route("**/api/appointment-message-settings/*/", route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { detail: "Try again" } }) : route.continue(), { times: 1 });
  await panel.getByRole("button", { name: ru["settings.appointmentMessages.saveScenario"], exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(text).toHaveValue("Changed {client_name}");
  await panel.getByRole("button", { name: ru["settings.appointmentMessages.saveScenario"], exact: true }).click();
  await expect.poll(async () => (await session.list<AppointmentMessageSetting>("appointment-message-settings")).some(row => row.template_text === "Changed {client_name}")).toBe(true);
  await scenarios.nth(1).click();
  await expect(text).toHaveValue("Keep other draft {time}");
  expect(settings).toHaveLength(3);
});

test("personal preferences load failure recovers and toggle persists for selected business", async ({ page }) => {
  const session = await crmSession(page);
  let fail = true;
  await page.route("**/api/notification-preferences/**", route => fail && route.request().method() === "GET" ? route.fulfill({ status: 503, json: { detail: "Unavailable" } }) : route.continue());
  await page.goto("/app/settings#notification-preferences");
  await expect(page).toHaveURL(/\/app\/account#notifications$/);
  const panel = page.locator("#notifications");
  await expect(panel.getByRole("alert")).toBeVisible({ timeout: 20_000 });
  await expect(panel.getByRole("switch")).toHaveCount(0);
  fail = false;
  await panel.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await panel.getByRole("switch").first().click();
  await expect(panel.getByRole("switch").first()).toHaveAttribute("aria-checked", "false");
  const result = await session.read("notification-preferences", { business: session.business, user: "me" });
  expect(result.results.some((row: { business: number; in_app_enabled: boolean }) => row.business === session.business && !row.in_app_enabled)).toBe(true);
});

test("custom definition created in settings reaches typed card fields and retains values on deactivate", async ({ page }, info) => {
  const session = await crmSession(page);
  const suffix = String(Date.now());
  const panel = await open(page, "custom-fields");
  await panel.getByRole("button", { name: ru["settings.redesign.addField"], exact: true }).click();
  const create = page.getByRole("dialog");
  const label = `Проверка ${suffix}`;
  await create.getByLabel(ru["settings.redesign.name"], { exact: true }).fill(label);
  await create.getByLabel(ru["settings.redesign.allEditRoles"], { exact: true }).uncheck();
  for (const role of ["owner", "admin", "manager", "specialist"] as const) await create.getByLabel(ru[`settings.role.${role}`] + " · " + ru["settings.redesign.action.update"], { exact: true }).uncheck();
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
  const card = settingsPanel.getByText(label, { exact: true }).locator('xpath=ancestor::div[contains(@class,"border-b")][1]');
  await card.getByRole("button", { name: ru["settings.workflow.fieldActions"] + " · " + label, exact: true }).click();
  await page.getByRole("menuitem", { name: ru["settings.disable"], exact: true }).click();
  await expect.poll(async () => (await session.read(`custom-fields/${definition.id}`)).is_active).toBe(false);
  expect((await session.read("custom-field-values", { business: session.business, definition: definition.id })).results[0].value_json.value).toBe("Saved from card");
  const optionCard = settingsPanel.getByText(multi.label, { exact: true }).locator('xpath=ancestor::div[contains(@class,"border-b")][1]');
  await optionCard.getByRole("button", { name: multi.label, exact: true }).click();
  const edit = page.getByRole("dialog");
  await edit.getByLabel(ru["settings.redesign.name"], { exact: true }).fill("Renamed choices");
  await edit.locator("summary").click();
  await expect(edit.getByText(ru["settings.customFieldRequiredMetadata"], { exact: false })).toBeVisible();
  await edit.getByRole("button", { name: ru["settings.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`custom-fields/${multi.id}`)).label).toBe("Renamed choices");
  expect((await session.read(`custom-fields/${multi.id}`)).options_json).toEqual(multi.options_json);
});

test("billing is cleared without changing subscription data and usage shows server metrics", async ({ page }) => {
  const session = await crmSession(page);
  const before = await session.read("billing/current-subscription", { business: session.business });
  const requests: string[] = [];
  page.on("request", request => { if (/\/api\/billing\/(current-subscription|plans|settings|request-plan-change)\//.test(request.url())) requests.push(request.method()); });
  const panel = await open(page, "billing");
  await expect(panel.locator("input,button,select,[role=combobox]")).toHaveCount(0);
  await expect(panel).toHaveText(ru["settings.section.billing"]);
  expect(requests).toEqual([]);
  const usage = await open(page, "usage");
  const metrics = await session.read("billing/entitlements", { business: session.business });
  for (const metric of metrics) {
    const label = ru[`settings.metric.${metric.metric}`];
    if (label) await expect(usage).toContainText(label);
    await expect(usage).toContainText(Number(metric.value).toLocaleString("ru-RU", { maximumFractionDigits: 2 }));
  }
  await expect(usage).toContainText(ru["settings.usageCurrent"]);
  await expect(usage).toContainText("МиБ");
  expect(await session.read("billing/current-subscription", { business: session.business })).toEqual(before);
});

test("role action scope saves independently and recovers from a rejected request", async ({ page }) => {
  const session = await crmSession(page);
  const roles = await session.list<BusinessRole>("team/roles");
  const role = roles.find(row => row.preset_key === "operator")!;
  const before = role.permissions;
  const permission = before.find(row => row.resource === "clients" && row.action === "view")!;
  expect(permission).toBeTruthy();
  const panel = await open(page, "roles");
  await panel.getByRole("combobox", { name: new RegExp("^" + ru["settings.role"]) }).click();
  await page.getByRole("option", { name: ru["settings.role.operator"], exact: true }).click();
  await panel.getByLabel(ru["common.search"], { exact: true }).fill(ru["settings.accessGroup.clients"]);
  const scope = panel.getByRole("combobox").nth(1);
  const nextScope = permission.scope === "business" ? "own" : "business";
  await scope.click();
  await page.getByRole("option", { name: ru[`settings.visibility.${nextScope}`], exact: true }).click();
  await page.route("**/api/team/role-permissions/*/", route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { detail: "Try again" } }) : route.continue(), { times: 1 });
  const save = panel.getByRole("button", { name: new RegExp("^" + ru["common.save"] + " ·") });
  await save.click();
  await expect(panel.getByRole("alert")).toBeVisible();
  expect((await session.read(`team/roles/${role.id}`)).permissions.find((row: {id: number}) => row.id === permission.id)).toEqual(permission);
  await save.click();
  await expect.poll(async () => (await session.read(`team/roles/${role.id}`)).permissions.find((row: {id: number}) => row.id === permission.id).scope).toBe(nextScope);
  const after = (await session.read(`team/roles/${role.id}`)).permissions;
  for (const item of before) {
    const updated = after.find((row: {id: number}) => row.id === item.id);
    expect(updated.is_allowed).toBe(item.is_allowed);
    if (item.id !== permission.id) expect(updated).toEqual(item);
  }
});

test("quick reply settings feed the Inbox draft without sending a message", async ({ page }) => {
  const session = await crmSession(page);
  const title = `Settings reply ${Date.now()}`;
  const text = "Prepared response from settings";
  const panel = await open(page, "quick-replies");
  await panel.getByRole("button", { name: ru["settings.redesign.newReply"], exact: true }).click();
  const form = page.getByRole("dialog");
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
  await panel.getByRole("button", { name: ru["settings.redesign.invite"], exact: true }).click();
  const invite = page.getByRole("dialog");
  await invite.getByLabel(ru["settings.loginEmail"], { exact: true }).fill(`settings-${suffix}@example.test`);
  await invite.getByLabel(ru["settings.fullName"], { exact: true }).fill(`Settings member ${suffix}`);
  await invite.getByRole("combobox", { name: new RegExp(ru["settings.delivery"]) }).click();
  await page.getByRole("option", { name: ru["settings.copyLink"], exact: true }).click();
  await invite.getByRole("button", { name: ru["settings.createInvite"], exact: true }).click();
  await expect(invite.getByText(ru["settings.inviteCreatedTitle"], { exact: true })).toBeVisible();
  const invitations = await session.list<{ id: number; email: string; role: string }>("team/invitations");
  const invitation = invitations.find(row => row.email === `settings-${suffix}@example.test`)!;
  expect(invitation.role).toBe("operator");
  await invite.getByRole("button", { name: ru["settings.revoke"], exact: true }).click();
  await page.getByRole("dialog").last().getByRole("button", { name: ru["settings.revoke"], exact: true }).click();
  await expect.poll(async () => (await session.read(`team/invitations/${invitation.id}`)).status).toBe("revoked");
  await expect(invite.getByRole("button", { name: ru["settings.revoke"], exact: true })).toHaveCount(0);
  await expect(invite.getByText(ru["status.revoked"], { exact: false })).toBeVisible();
  await invite.getByRole("button", { name: ru["common.close"], exact: true }).first().click();
  await panel.getByRole("button", { name: ru["settings.departments"], exact: true }).click();
  const name = panel.getByLabel(ru["settings.redesign.name"], { exact: true });
  await name.fill(`Settings department ${suffix}`);
  await name.locator("xpath=ancestor::form").getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(panel.getByText(`Settings department ${suffix}`, { exact: true })).toBeVisible();
  const members = await session.list<{ id: number; role: string; is_active: boolean; user: { full_name: string; email: string } }>("team/members");
  const member = members.find(item => item.role === "operator" && item.is_active)!;
  await panel.getByRole("button", { name: ru["settings.redesign.employees"], exact: true }).click();
  await panel.getByRole("button").filter({ hasText: member.user.email }).click();
  for (const enabled of [false, true]) {
    await page.getByTestId("team-access-toggle").click();
    const dialog = page.getByRole("dialog").last();
    await dialog.getByRole("button", { name: ru[enabled ? "teamAccess.enable" : "teamAccess.disable"], exact: true }).click();
    await expect.poll(async () => (await session.read(`team/members/${member.id}`)).is_active).toBe(enabled);
  }
});
