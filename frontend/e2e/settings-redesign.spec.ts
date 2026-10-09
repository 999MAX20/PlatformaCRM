import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import type { BusinessRole, CustomFieldDefinition } from "../src/types";

test.use({ actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

async function open(page: Page, section: string) {
  await page.goto(`/app/settings#${section}`);
  await expect(page.getByTestId("settings-workspace-ready")).toBeVisible();
  const panel = page.locator(`#${section}`);
  await expect(panel).toBeVisible();
  await expect(panel.locator(".platforma-loading")).toHaveCount(0);
  return panel;
}

async function navigate(page: Page, section: string) {
  const nav = page.locator(".settings-workspace > aside");
  const label = ru[`settings.section.${section}` as keyof typeof ru];
  if (await nav.getByRole("combobox").isVisible()) {
    await nav.getByRole("combobox").click();
    await nav.getByRole("option", { name: label, exact: true }).click();
  } else await nav.getByRole("link", { name: label, exact: true }).click();
  await expect(page.locator(`#${section}`)).toBeVisible();
}

test("navigation retains independent drafts and drawer keyboard focus returns to its opener", async ({ page }, info) => {
  const session = await crmSession(page);
  const before = await session.read(`businesses/${session.business}`);
  const profile = await open(page, "business-profile");
  const city = `Draft city ${Date.now()}`;
  await profile.getByLabel(ru["businessForm.city"], { exact: true }).fill(city);
  await navigate(page, "quick-replies");
  const opener = page.getByRole("button", { name: ru["settings.redesign.newReply"], exact: true });
  await opener.focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog");
  await drawer.getByLabel(ru["settings.templateTitle"], { exact: true }).fill("Unsent draft");
  await drawer.getByLabel(ru["settings.templateText"], { exact: true }).fill("Retained response");
  await expect(drawer.getByRole("button", { name: ru["settings.add"], exact: true })).toBeInViewport();
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(opener).toBeFocused();
  await navigate(page, "business-profile");
  await expect(profile.getByLabel(ru["businessForm.city"], { exact: true })).toHaveValue(city);
  expect((await session.read(`businesses/${session.business}`)).city).toBe(before.city);
  await expect(profile.getByRole("button", { name: ru["businessForm.save"], exact: true })).toBeInViewport();
  await page.screenshot({ path: info.outputPath("company-draft-save-bar.png"), fullPage: false });
  await page.goBack();
  await expect(page.locator("#quick-replies")).toBeVisible();
  await opener.click();
  await expect(drawer.getByLabel(ru["settings.templateTitle"], { exact: true })).toHaveValue("Unsent draft");
  await expect(drawer.getByRole("textbox", { name: ru["settings.templateText"], exact: true })).toHaveValue("Retained response");
});

test("custom field access cannot accidentally widen when the final selected role is removed", async ({ page }, info) => {
  const session = await crmSession(page);
  const panel = await open(page, "custom-fields");
  await panel.getByRole("button", { name: ru["settings.redesign.addField"], exact: true }).click();
  const drawer = page.getByRole("dialog");
  const label = `Access field ${Date.now()}`;
  await drawer.getByLabel(ru["settings.redesign.name"], { exact: true }).fill(label);
  await drawer.getByLabel(ru["settings.redesign.allEditRoles"], { exact: true }).uncheck();
  for (const role of ["owner", "admin", "manager", "operator", "specialist"] as const) {
    await drawer.getByLabel(ru[`settings.role.${role}`] + " · " + ru["settings.redesign.action.update"], { exact: true }).uncheck();
  }
  await drawer.getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(drawer.getByRole("alert")).toHaveText(ru["settings.redesign.noRolesSelected"]);
  expect((await session.list<CustomFieldDefinition>("custom-fields")).some(field => field.label === label)).toBe(false);
  await expect(drawer.getByRole("button", { name: ru["settings.add"], exact: true })).toBeInViewport();
  await page.screenshot({ path: info.outputPath("field-access-error.png"), fullPage: false });
  await drawer.getByLabel(ru["settings.role.operator"] + " · " + ru["settings.redesign.action.update"], { exact: true }).check();
  await drawer.getByRole("button", { name: ru["settings.add"], exact: true }).click();
  await expect(drawer).toHaveCount(0);
  const field = (await session.list<CustomFieldDefinition>("custom-fields")).find(item => item.label === label)!;
  expect(field.permissions_json).toEqual({ view_roles: [], edit_roles: ["operator"] });
});

test("missing role override is explicit, saves through POST and owner permissions remain read only", async ({ page }, info) => {
  const session = await crmSession(page);
  const role = await session.create<BusinessRole>("team/roles", {
    name: `Custom access ${Date.now()}`, is_active: true,
    permissions_json: { clients: { view: "business" } },
  });
  const panel = await open(page, "roles");
  const selector = panel.getByRole("combobox", { name: new RegExp("^" + ru["settings.role"]) }).first();
  await selector.click();
  await page.getByRole("option", { name: role.name, exact: true }).click();
  await panel.locator("summary").filter({ hasText: ru["permissions.resource.clients"] }).click();
  const name = ru["permissions.resource.clients"] + " · " + ru["settings.redesign.action.view"];
  const checkbox = panel.getByRole("checkbox", { name: name + " · " + ru["settings.redesign.access"], exact: true });
  await expect(checkbox).toHaveJSProperty("indeterminate", true);
  const requests: unknown[] = [];
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/api/team/role-permissions/")) requests.push(request.postDataJSON()); });
  await checkbox.click();
  await panel.getByRole("button", { name: ru["common.save"] + " · " + name, exact: true }).click();
  await expect.poll(async () => (await session.read(`team/roles/${role.id}`)).permissions.length).toBe(1);
  const updated = await session.read(`team/roles/${role.id}`);
  expect(updated.permissions[0]).toMatchObject({ resource: "clients", action: "view", scope: "own", is_allowed: true });
  expect(requests).toHaveLength(1);
  await page.screenshot({ path: info.outputPath("role-action-matrix.png"), fullPage: true });
  await selector.click();
  await page.getByRole("option", { name: ru["settings.role.owner"], exact: true }).click();
  await expect(panel.getByRole("checkbox").first()).toBeChecked();
  await expect(panel.getByRole("checkbox").first()).toBeDisabled();
  await expect(panel.getByRole("button", { name: new RegExp("^" + ru["common.save"] + " ·") })).toHaveCount(0);
});

test("invitation access preview follows the configured role and navigation preserves invitation draft", async ({ page }, info) => {
  await crmSession(page);
  const panel = await open(page, "team-access");
  const invite = panel.getByRole("button", { name: ru["settings.redesign.invite"], exact: true });
  await invite.click();
  const drawer = page.getByRole("dialog");
  await drawer.getByLabel(ru["settings.fullName"], { exact: true }).fill("Draft colleague");
  await drawer.getByLabel(ru["settings.loginEmail"], { exact: true }).fill("draft-colleague@example.test");
  await expect(drawer.getByText(ru["settings.redesign.rolePreview"], { exact: true })).toBeVisible();
  await expect(drawer.locator(".platforma-loading")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("invitation-role-preview.png"), fullPage: false });
  await drawer.getByRole("button", { name: ru["settings.redesign.configureRole"], exact: true }).click();
  await expect(page.locator("#roles")).toBeVisible();
  await expect(page.locator("#roles").getByRole("combobox").first()).toContainText(ru["settings.role.operator"]);
  await page.locator("#roles").getByRole("button", { name: ru["settings.workflow.backToInvitation"], exact: true }).click();
  await expect(drawer.getByLabel(ru["settings.fullName"], { exact: true })).toHaveValue("Draft colleague");
  await expect(drawer.getByLabel(ru["settings.loginEmail"], { exact: true })).toHaveValue("draft-colleague@example.test");
});

test("security tabs keep error and retry local instead of showing a false empty result", async ({ page }, info) => {
  await crmSession(page);
  let fail = true;
  await page.route("**/api/security/login-history/**", route => fail ? route.fulfill({ status: 503, json: { detail: "Unavailable" } }) : route.continue());
  const panel = await open(page, "security-center");
  await panel.getByRole("button", { name: ru["settings.redesign.loginsTab"], exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(panel.getByText(ru["settings.noLoginHistory"], { exact: true })).toHaveCount(0);
  fail = false;
  await panel.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("security-logins.png"), fullPage: true });
  await panel.getByLabel(ru["settings.workflow.failedOnly"], { exact: true }).check();
  await expect(panel.getByText(ru["settings.loginStatus.success"], { exact: true })).toHaveCount(0);
  await expect(panel.getByText(ru["settings.noLoginHistory"], { exact: true })).toHaveCount(0);
  await panel.getByLabel(ru["settings.workflow.failedOnly"], { exact: true }).uncheck();
  await panel.getByRole("button", { name: ru["settings.redesign.supportTab"], exact: true }).click();
  await expect(panel.getByText(ru["settings.noSupportGrants"], { exact: true })).toBeVisible();
});
