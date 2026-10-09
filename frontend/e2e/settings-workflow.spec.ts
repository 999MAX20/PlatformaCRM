import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import type { CustomFieldDefinition } from "../src/types";
import type { BusinessRole } from "../src/types";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

test.use({ actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

test("employee opens assigned role, edits its existing permissions and returns to the same employee", async ({ page }) => {
  const session = await crmSession(page);
  const members = await session.list<{ id: number; role: string; business_role: number; user: { email: string } }>("team/members");
  const member = members.find(item => item.role === "operator")!;
  const roles = await session.list<BusinessRole>("team/roles");
  const role = roles.find(item => item.id === member.business_role) || roles.find(item => item.preset_key === member.role)!;
  await page.goto("/app/settings#team-access");
  await page.locator("#team-access").getByRole("button").filter({ hasText: member.user.email }).click();
  await page.getByRole("dialog").getByRole("button", { name: ru["settings.workflow.editRolePermissions"], exact: true }).click();
  const panel = page.locator("#roles");
  await expect(panel.getByRole("combobox", { name: new RegExp("^" + ru["settings.role"]), exact: false })).toContainText(role.is_system ? ru[`settings.role.${role.preset_key}`] : role.name);
  await expect(panel.getByText(ru["settings.redesign.roleApplies"], { exact: true })).toBeVisible();
  await panel.getByLabel(ru["common.search"], { exact: true }).fill(ru["permissions.resource.clients"]);
  const name = ru["permissions.resource.clients"] + " · " + ru["settings.redesign.action.view"];
  const checkbox = panel.getByRole("checkbox", { name: name + " · " + ru["settings.redesign.access"], exact: true });
  const before = await checkbox.isChecked();
  await checkbox.click();
  await panel.getByRole("button", { name: ru["common.save"] + " · " + name, exact: true }).click();
  await expect.poll(async () => (await session.read(`team/roles/${role.id}`)).permissions.find((item: {resource: string; action: string}) => item.resource === "clients" && item.action === "view").is_allowed).toBe(!before);
  await panel.getByRole("button", { name: ru["settings.workflow.backToEmployee"], exact: true }).click();
  await expect(page.getByRole("dialog").getByText(member.user.email, { exact: true })).toBeVisible();
  expect((await session.list<BusinessRole>("team/roles")).map(item => item.id)).toEqual(roles.map(item => item.id));
});

test("financial source is configured in Integrations with error recovery and profile preservation", async ({ page }) => {
  const session = await crmSession(page);
  const before = await session.read(`businesses/${session.business}`);
  const connector = await session.create<{ id: number; name: string }>("business-connectors", { provider: "1c", capability: "finance", auth_type: "none", name: `Finance ${Date.now()}` });
  await page.goto("/app/integrations");
  const panel = page.locator("#financial-source");
  await panel.getByRole("combobox", { name: new RegExp("^" + ru["aiHistory.sourceSetting"]), exact: false }).click();
  await page.getByRole("option", { name: ru["aiHistory.external"], exact: true }).click();
  await panel.getByRole("combobox", { name: new RegExp("^" + ru["aiHistory.integration"]), exact: false }).click();
  await page.getByRole("option", { name: connector.name, exact: true }).click();
  await page.route(`**/api/businesses/${session.business}/`, route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { detail: "Try again" } }) : route.continue(), { times: 1 });
  await panel.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  expect((await session.read(`businesses/${session.business}`)).financial_source_mode).toBe(before.financial_source_mode);
  await panel.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`businesses/${session.business}`)).financial_connector).toBe(connector.id);
  const after = await session.read(`businesses/${session.business}`);
  expect(after.financial_source_mode).toBe("external");
  for (const key of ["name", "slug", "currency", "timezone", "legal_name", "invoice_email", "settings_json"]) expect(after[key]).toEqual(before[key]);
  await page.reload();
  await expect(panel.getByRole("combobox", { name: new RegExp("^" + ru["aiHistory.integration"]), exact: false })).toContainText(connector.name);
});

test("Account notification defaults and updates are isolated by user and business", async ({ page }) => {
  const session = await crmSession(page);
  const otherBusiness = await session.create<{ id: number }>("businesses", { name: `ZZ notification business ${Date.now()}`, business_type: "other", slug: `notification-${Date.now()}` });
  const otherPreference = await session.create<{ id: number }>("notification-preferences", { business: otherBusiness.id, user: session.userId, category: "outreach", in_app_enabled: false });
  const members = await session.list<{ role: string; user: { id: number } }>("team/members");
  const otherUser = members.find(item => item.role === "operator")!.user.id;
  const colleaguePreference = await session.create<{ id: number }>("notification-preferences", { user: otherUser, category: "outreach", in_app_enabled: false });
  await page.goto("/app/account#notifications");
  const toggle = page.locator("#notifications").getByRole("switch", { name: ru["settings.notifications.category.outreach"], exact: true });
  await expect(toggle).toBeChecked();
  await toggle.click();
  await expect(toggle).not.toBeChecked();
  const result = await session.read("notification-preferences", { business: session.business, user: "me" });
  expect(result.results.find((item: {category: string}) => item.category === "outreach")).toMatchObject({ business: session.business, user: session.userId, in_app_enabled: false });
  expect((await session.read(`notification-preferences/${otherPreference.id}`)).in_app_enabled).toBe(false);
  expect((await session.read(`notification-preferences/${colleaguePreference.id}`)).in_app_enabled).toBe(false);
});

test("empty Inbox replies link to creation and return preserves the unsent draft", async ({ page }) => {
  const session = await crmSession(page);
  for (const reply of await session.list<{ id: number }>("quick-replies")) {
    const result = await page.request.patch(`${api}/api/quick-replies/${reply.id}/`, { headers: session.headers, data: { is_active: false } });
    expect(result.ok()).toBeTruthy();
  }
  const conversation = (await session.list<{ id: number }>("inbox/conversations"))[0];
  const before = await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`);
  await page.goto(`/app/conversations/${conversation.id}`);
  const composer = page.getByTestId("inbox-action-composer");
  await composer.fill("Existing unsent draft");
  await page.getByRole("button", { name: ru["conversations.quickRepliesButton"], exact: true }).click();
  await page.getByRole("link", { name: ru["settings.workflow.createQuickReply"], exact: true }).click();
  const title = `Linked reply ${Date.now()}`;
  await page.locator("#quick-replies").getByRole("button", { name: ru["settings.redesign.newReply"], exact: true }).click();
  const drawer = page.getByRole("dialog");
  await drawer.getByLabel(ru["settings.templateTitle"], { exact: true }).fill(title);
  await drawer.getByLabel(ru["settings.templateText"], { exact: true }).fill("Added reply");
  await drawer.getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(drawer).toHaveCount(0);
  await page.goBack();
  await expect(composer).toHaveValue("Existing unsent draft");
  await page.getByRole("button", { name: ru["conversations.quickRepliesButton"], exact: true }).click();
  await page.getByRole("button").filter({ hasText: title }).click();
  await expect(composer).toHaveValue(/Existing unsent draft\s+Added reply/);
  expect((await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`)).map(item => item.id)).toEqual(before.map(item => item.id));
});

for (const entity of ["client", "lead", "deal", "appointment"] as const) {
  test(`custom ${entity} field reaches the full entity page and keeps its saved value`, async ({ page }, info) => {
    const session = await crmSession(page);
    const stamp = Date.now();
    const label = `Дополнительное поле ${entity} ${stamp}`;
    await page.goto("/app/settings#custom-fields");
    const panel = page.locator("#custom-fields");
    await panel.getByRole("button", { name: ru[`settings.customFieldEntity.${entity}`], exact: true }).click();
    await expect(panel.getByText(ru[`settings.workflow.fieldPlacement.${entity}`], { exact: true })).toBeVisible();
    await panel.getByRole("button", { name: ru["settings.redesign.addField"], exact: true }).click();
    const editor = page.getByRole("dialog");
    await editor.getByLabel(ru["settings.redesign.name"], { exact: true }).fill(label);
    await editor.getByRole("button", { name: ru["settings.add"], exact: true }).click();
    await expect(editor).toHaveCount(0);
    await expect(panel.getByRole("button", { name: label, exact: true })).toBeVisible();
    const definition = (await session.list<CustomFieldDefinition>("custom-fields")).find(item => item.label === label)!;
    expect(definition.entity_type).toBe(entity);
    await page.screenshot({ path: info.outputPath(`settings-${entity}-columns.png`), fullPage: true });
    const client = await session.create<{ id: number }>("clients", { full_name: `Field workflow ${stamp}` });
    let id = client.id;
    let path = "clients";
    if (entity === "lead") {
      id = (await session.create<{ id: number }>("leads", { client: client.id, message: "Field workflow", responsible_user: session.userId })).id;
      path = "leads";
    }
    if (entity === "deal") {
      const pipeline = (await session.list<{ id: number }>("pipelines"))[0];
      const stage = (await session.list<{ id: number; pipeline: number; is_won: boolean; is_lost: boolean }>("pipeline-stages")).find(item => item.pipeline === pipeline.id && !item.is_won && !item.is_lost)!;
      id = (await session.create<{ id: number }>("deals", { client: client.id, pipeline: pipeline.id, stage: stage.id, title: `Field deal ${stamp}`, amount: "100" })).id;
      path = "deals";
    }
    if (entity === "appointment") {
      const resource = await session.create<{ id: number }>("resources", { name: `Field specialist ${stamp}`, weekly_schedule: Array.from({ length: 7 }, (_, weekday) => ({ weekday, start_time: "09:00", end_time: "20:00", is_day_off: false })) });
      const service = await session.create<{ id: number }>("services", { name: `Field service ${stamp}`, duration_minutes: 30, price_from: 100 });
      const date = new Date(Date.now() + 4 * 86400_000).toISOString().slice(0, 10);
      const slots = await session.read("appointments/available-slots", { business_id: session.business, service_id: service.id, resource_id: resource.id, date });
      expect(slots.length).toBeGreaterThan(0);
      id = (await session.create<{ id: number }>("appointments", { client: client.id, service: service.id, resource: resource.id, start_at: slots[0].start_at })).id;
      path = "calendar";
    }
    await page.goto(`/app/${path}/${id}`);
    const input = page.getByLabel(label, { exact: true });
    await expect(input).toBeVisible();
    await input.fill(`Saved ${entity} value`);
    await page.getByRole("button", { name: ru["crmCard.saveFields"], exact: true }).click();
    await expect.poll(async () => {
      const result = await session.read("custom-field-values", { business: session.business, entity_type: entity, entity_id: String(id), definition: definition.id });
      return result.results[0]?.value_json.value;
    }).toBe(`Saved ${entity} value`);
    await page.reload();
    await expect(input).toHaveValue(`Saved ${entity} value`);
    await page.screenshot({ path: info.outputPath(`${entity}-saved-value.png`), fullPage: true });
  });
}
