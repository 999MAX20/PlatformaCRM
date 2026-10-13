import { expect, request, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { BusinessRole, TeamMember } from "../src/types";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

for (const [locale, t] of Object.entries({ ru, kk, en })) {
  test(`legacy assignment is explicit, retryable and changes actual access ${locale}`, async ({ page }, info) => {
    const session = await crmSession(page);
    const members = await session.list<TeamMember>("team/members");
    const member = members.find(item => item.user.email === "business_operator@example.com")!;
    const sibling = members.find(item => item.user.email === "business_manager@example.com")!;
    const roles = await session.list<BusinessRole>("team/roles");
    const role = roles.find(item => item.preset_key === "operator")!;
    const memberUrl = `${api}/api/team/members/${member.id}/`;
    for (const target of [member, sibling]) {
      const response = await page.request.patch(`${api}/api/team/members/${target.id}/`, { headers: session.headers, data: { role: "operator", business_role: null } });
      expect(response.ok(), await response.text()).toBeTruthy();
    }
    const permission = role.permissions.find(item => item.resource === "clients" && item.action === "view")!;
    const deny = await page.request.patch(`${api}/api/team/role-permissions/${permission.id}/`, { headers: session.headers, data: { is_allowed: false } });
    expect(deny.ok(), await deny.text()).toBeTruthy();
    const client = await session.create<{ id: number }>("clients", { full_name: `Assignment proof ${locale}` });
    async function actualAccess(email: string, allowed: boolean) {
      const actor = await request.newContext();
      const login = await actor.post(`${api}/api/auth/token/`, { data: { email, password: process.env.E2E_PASSWORD || "ZaniTest123!" } });
      expect(login.ok()).toBeTruthy();
      const headers = { Authorization: `Bearer ${(await login.json()).access}` };
      const profile = await (await actor.get(`${api}/api/auth/me/`, { headers })).json();
      expect(profile.effective_permissions[String(session.business)].some((item: { resource: string; action: string }) => item.resource === "clients" && item.action === "view")).toBe(allowed);
      const response = await actor.get(`${api}/api/clients/`, { headers });
      expect(response.status()).toBe(200);
      const rows = (await response.json()).results;
      expect(rows.some((item: { id: number }) => item.id === client.id)).toBe(allowed);
      if (!allowed) expect(rows).toEqual([]);
      // TenantModelViewSet hides denied objects from its queryset, so detail is 404.
      expect((await actor.get(`${api}/api/clients/${client.id}/`, { headers })).status()).toBe(allowed ? 200 : 404);
      await actor.dispose();
    }
    await actualAccess(member.user.email, true);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/settings#team-access");
    await page.locator("#team-access").getByRole("button").filter({ hasText: member.user.email }).click();
    const drawer = page.getByRole("dialog");
    const save = drawer.getByRole("button", { name: t["common.save"], exact: true });
    const edit = drawer.getByRole("button", { name: t["settings.workflow.editRolePermissions"], exact: true });
    await expect(save).toBeEnabled();
    await expect(edit).toBeDisabled();
    await expect(drawer.getByText(t["settings.workflow.saveRoleFirst"], { exact: true })).toBeVisible();
    expect((await session.read(`team/members/${member.id}`)).business_role).toBeNull();
    await page.screenshot({ path: info.outputPath(`legacy-${locale}.png`), fullPage: true });
    await page.route(memberUrl, async route => {
      if (route.request().method() === "PATCH") await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary assignment failure" }) });
      else await route.continue();
    });
    await save.focus(); await page.keyboard.press("Enter");
    await expect(drawer.getByRole("alert")).toBeVisible();
    await expect(save).toBeEnabled();
    await expect(edit).toBeDisabled();
    expect((await session.read(`team/members/${member.id}`)).business_role).toBeNull();
    await page.unroute(memberUrl);
    await save.focus(); await page.keyboard.press("Enter");
    await expect(edit).toBeEnabled();
    await expect(save).toBeDisabled();
    expect((await session.read(`team/members/${member.id}`)).business_role).toBe(role.id);
    await actualAccess(member.user.email, false);
    expect((await session.read(`team/members/${sibling.id}`)).business_role).toBeNull();
    await actualAccess(sibling.user.email, true);
    await edit.focus(); await page.keyboard.press("Enter");
    await expect(page.locator("#roles")).toBeVisible();
    await page.locator("#roles").getByRole("button", { name: t["settings.workflow.backToEmployee"], exact: true }).click();
    await expect(drawer.getByText(member.user.email, { exact: true })).toBeVisible();
    await expect(edit).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test("assigned custom role survives opening, cancelling and returning from its editor", async ({ page }) => {
  const session = await crmSession(page);
  const member = (await session.list<TeamMember>("team/members")).find(item => item.role === "specialist")!;
  const custom = await session.create<BusinessRole>("team/roles", { name: `Custom specialist ${Date.now()}`, preset_key: "specialist", is_system: false });
  const response = await page.request.patch(`${api}/api/team/members/${member.id}/`, { headers: session.headers, data: { business_role: custom.id } });
  expect(response.ok(), await response.text()).toBeTruthy();
  await page.goto("/app/settings#team-access");
  const row = page.locator("#team-access").getByRole("button").filter({ hasText: member.user.email });
  await row.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByRole("button", { name: ru["common.save"], exact: true })).toBeDisabled();
  await expect(drawer.getByRole("combobox")).toContainText(custom.name);
  await drawer.getByRole("button", { name: ru["settings.workflow.editRolePermissions"], exact: true }).click();
  await expect(page.locator("#roles").getByRole("combobox", { name: new RegExp("^" + ru["settings.role"]) })).toContainText(custom.name);
  await page.locator("#roles").getByRole("button", { name: ru["settings.workflow.backToEmployee"], exact: true }).click();
  await drawer.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  expect((await session.read(`team/members/${member.id}`)).business_role).toBe(custom.id);
  await page.locator("#team-access").getByRole("button").filter({ hasText: "business_owner@example.com" }).click();
  await expect(drawer.getByText(ru["settings.redesign.ownerAccess"], { exact: true })).toBeVisible();
  await expect(drawer.getByText(ru["settings.workflow.saveRoleFirst"], { exact: true })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: ru["common.save"], exact: true })).toHaveCount(0);
});
