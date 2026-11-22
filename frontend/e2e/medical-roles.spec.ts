import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.use({ actionTimeout: 15_000 });
async function login(page: Page, language: string, email = "medical-role-owner@example.test") {
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const authenticated = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await authenticated).json()).access as string;
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/settings#medical-access");
  return token;
}

test("roles: self restriction, read recovery, stale revision and denial clear private state", async ({ page }, info) => {
  test.setTimeout(120_000);
  const t = en;
  const token = await login(page, "en");
  const headers = { Authorization: `Bearer ${token}` };
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/role-management/`;
  const workspace = page.getByTestId("medical-role-workspace");
  await workspace.getByRole("listitem").filter({ hasText: "Synthetic owner" }).getByRole("button").click();
  const panel = page.getByTestId("medical-role-member-panel");
  await expect(panel.getByRole("button", { name: t["medical.roles.assign"], exact: true })).toBeDisabled();
  await page.keyboard.press("Escape");
  let reads = 0;
  await page.route("**/api/medical/role-management/member-context/**", async route => {
    if (++reads === 1) return route.fulfill({ status: 503, json: { detail: "Synthetic outage" } });
    return route.continue();
  });
  const member = (await (await page.request.get(root + "members/?business_id=1&query=Synthetic%20role%20target%206", { headers })).json()).results[0];
  await workspace.getByRole("listitem").filter({ hasText: "Synthetic role target 6" }).getByRole("button").click();
  await page.getByRole("dialog").getByRole("button", { name: t["common.retry"], exact: true }).click();
  await expect(panel).toBeVisible();
  const context = await (await page.request.get(root + `member-context/?business_id=1&member_id=${member.id}`, { headers })).json();
  const created = await page.request.post(root + "roles/", { headers: { ...headers, "Idempotency-Key": "synthetic-stale-definition" }, data: {
    business_id: 1, name: "Synthetic stale role", kind: "head", permissions: [{ resource: "medical_records", action: "view", scope: "own" }],
  } });
  expect(created.ok()).toBe(true);
  const role = { ...(await created.json()), name: "Synthetic stale role" };
  await panel.getByRole("button", { name: t["medical.roles.assign"], exact: true }).click();
  const form = page.getByTestId("medical-role-command");
  await form.getByRole("combobox", { name: new RegExp(`^${t["medical.roles.role"]}(?:\\s|$)`) }).click();
  await page.getByRole("option", { name: role.name, exact: true }).click();
  await form.getByRole("checkbox", { name: "First", exact: true }).check();
  await form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true }).fill("Synthetic stale form");
  const branches = await (await page.request.get(root + `branches/?business_id=1&member_id=${member.id}`, { headers })).json();
  const changed = await page.request.post(root + "assign/", { headers: { ...headers, "Idempotency-Key": "synthetic-concurrent-role" }, data: {
    business_id: 1, member_id: member.id, role_id: role.id, branch_ids: [branches.results[0].id], all_branches: false,
    expected_revision: context.assignment?.revision ?? 0, reason: "Synthetic concurrent assignment",
  } });
  expect(changed.ok()).toBe(true);
  await form.getByRole("button", { name: t["medical.roles.assign"], exact: true }).click();
  await expect(form.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
  await expect(form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true })).toBeDisabled();
  await expect(form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true })).toHaveValue("Synthetic stale form");
  await page.screenshot({ path: info.outputPath("stale-role.png") });
  page.once("dialog", dialog => dialog.accept());
  await form.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(panel.getByTestId("medical-role-current")).toContainText(t["medical.roles.assigned"]);
  await panel.getByRole("button", { name: t["medical.roles.revoke"], exact: true }).click();
  await form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true }).fill("Synthetic private revocation basis");
  await page.route("**/api/medical/role-management/revoke/", route => route.fulfill({ status: 403, json: { detail: "Synthetic permission revoked" } }));
  await form.getByRole("button", { name: t["medical.roles.revoke"], exact: true }).click();
  await expect(workspace).toHaveCount(0);
  await expect(page.getByText("Synthetic private revocation basis")).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
const dictionaries = { ru, kk, en };
let index = -1;
for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  const target = ++index;
  test(`roles ${language} ${mobile ? "mobile" : "desktop"}: define, assign, revoke and history`, async ({ page }, info) => {
    test.setTimeout(120_000);
    const t = dictionaries[language];
    await page.setViewportSize(mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 });
    await login(page, language);
    const workspace = page.getByTestId("medical-role-workspace");
    await workspace.getByRole("button", { name: t["medical.roles.create"], exact: true }).click();
    const form = page.getByTestId("medical-role-command");
    const name = `Synthetic deputy ${language} ${mobile}`;
    await form.getByRole("textbox", { name: t["medical.roles.name"], exact: true }).fill(name);
    await form.getByRole("group", { name: t["medical.roles.resource.medical_records"], exact: true })
      .getByRole("checkbox", { name: t["medical.roles.action.view"], exact: true }).check();
    page.once("dialog", dialog => dialog.dismiss());
    await page.keyboard.press("Escape");
    await expect(form.getByRole("textbox", { name: t["medical.roles.name"], exact: true })).toHaveValue(name);
    const keys: string[] = [];
    await page.route("**/api/medical/role-management/roles/", async route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      if (keys.length === 1) await route.fulfill({ status: 503, json: { detail: "Synthetic outage" } });
      else await route.continue();
    });
    const create = form.getByRole("button", { name: t["medical.roles.create"], exact: true });
    await create.click();
    await expect(form.getByRole("alert")).toContainText(t["actions.errorTemporary"]);
    await expect(form.getByRole("textbox", { name: t["medical.roles.name"], exact: true })).toHaveValue(name);
    await page.screenshot({ path: info.outputPath("definition-recovery.png") });
    await form.getByRole("textbox", { name: t["medical.roles.name"], exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath("definition-top.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="medical-role-command"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await create.click();
    await expect(form).toHaveCount(0);
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await expect(page.locator("#medical-role-create")).toBeFocused();
    const row = workspace.getByRole("listitem").filter({ hasText: `Synthetic role target ${target}` });
    await row.getByRole("button", { name: t["medical.roles.memberAccess"], exact: true }).click();
    const panel = page.getByTestId("medical-role-member-panel");
    await expect(panel).toContainText(t["medical.roles.notAssigned"]);
    await expect(panel).toContainText(t["medical.roles.noHistory"]);
    await panel.getByRole("button", { name: t["medical.roles.assign"], exact: true }).click();
    await form.getByRole("combobox", { name: new RegExp(`^${t["medical.roles.role"]}(?:\\s|$)`) }).click();
    await page.getByRole("option", { name, exact: true }).click();
    await expect(form.getByRole("checkbox", { name: t["branches.allFuture"], exact: true })).toBeDisabled();
    await form.getByRole("checkbox", { name: "First", exact: true }).check();
    const basis = `Synthetic appointment ${language} ${mobile}\nExplicit branch scope`;
    await form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true }).fill(basis);
    await page.screenshot({ path: info.outputPath("assignment.png") });
    await form.getByRole("button", { name: t["medical.roles.assign"], exact: true }).click();
    await expect(form).toHaveCount(0);
    await expect(panel.getByTestId("medical-role-current")).toContainText(name);
    await expect(panel.getByTestId("medical-role-current")).toContainText("First");
    await expect(panel.getByRole("region", { name: t["medical.roles.history"] })).toContainText(basis);
    await panel.getByRole("button", { name: t["medical.roles.revoke"], exact: true }).click();
    await form.getByRole("textbox", { name: t["medical.roles.reason"], exact: true }).fill("Synthetic revocation");
    await form.getByRole("button", { name: t["medical.roles.revoke"], exact: true }).click();
    await expect(form).toHaveCount(0);
    await expect(panel.getByTestId("medical-role-current")).toContainText(t["medical.roles.revoked"]);
    await expect(panel.getByRole("region", { name: t["medical.roles.history"] }).getByRole("listitem")).toHaveCount(2);
    await page.screenshot({ path: info.outputPath("revocation-history.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="medical-role-member-panel"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await expect(row.getByRole("button")).toBeFocused();
  });
}

test("roles boundaries: nonowner has no management entry or API access", async ({ page }) => {
  const token = await login(page, "en", "medical-role-doctor@example.test");
  await expect(page.getByTestId("settings-workspace-ready")).toBeVisible();
  await expect(page.getByTestId("medical-role-workspace")).toHaveCount(0);
  await expect(page.getByRole("button", { name: en["settings.section.medical-access"], exact: true })).toHaveCount(0);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/role-management/workspace/?business_id=1`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(403);
});

test("roles boundaries: module disable preserves revocation and history", async ({ page }, info) => {
  test.setTimeout(120_000);
  const token = await login(page, "en");
  const headers = { Authorization: `Bearer ${token}` };
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/role-management/`;
  const member = (await (await page.request.get(root + "members/?business_id=1&query=Synthetic%20role%20target%206", { headers })).json()).results[0];
  const context = await (await page.request.get(root + `member-context/?business_id=1&member_id=${member.id}`, { headers })).json();
  const created = await page.request.post(root + "roles/", { headers: { ...headers, "Idempotency-Key": "synthetic-disabled-definition" }, data: {
    business_id: 1, name: "Synthetic disabled module role", kind: "head", permissions: [{ resource: "medical_records", action: "view", scope: "own" }],
  } });
  expect(created.ok()).toBe(true);
  const branches = await (await page.request.get(root + `branches/?business_id=1&member_id=${member.id}`, { headers })).json();
  const assigned = await page.request.post(root + "assign/", { headers: { ...headers, "Idempotency-Key": "synthetic-disabled-assignment" }, data: {
    business_id: 1, member_id: member.id, role_id: (await created.json()).id, branch_ids: [branches.results[0].id], all_branches: false,
    expected_revision: context.assignment?.revision ?? 0, reason: "Synthetic pre-disable assignment",
  } });
  expect(assigned.ok()).toBe(true);
  const changeModule = (action: string) => execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", action], { env: process.env, windowsHide: true, stdio: "pipe" });
  try {
    changeModule("disable-role-module");
    await page.reload();
    const workspace = page.getByTestId("medical-role-workspace");
    await expect(workspace).toContainText(en["medical.roles.moduleDisabled"]);
    await expect(workspace.getByRole("button", { name: en["medical.roles.create"], exact: true })).toBeDisabled();
    await workspace.getByRole("listitem").filter({ hasText: "Synthetic role target 6" }).getByRole("button").click();
    const panel = page.getByTestId("medical-role-member-panel");
    await expect(panel.getByRole("button", { name: en["medical.roles.assign"], exact: true })).toBeDisabled();
    await panel.getByRole("button", { name: en["medical.roles.revoke"], exact: true }).click();
    const form = page.getByTestId("medical-role-command");
    await form.getByRole("textbox", { name: en["medical.roles.reason"], exact: true }).fill("Synthetic disabled module revocation");
    await form.getByRole("button", { name: en["medical.roles.revoke"], exact: true }).click();
    await expect(form).toHaveCount(0);
    await expect(panel.getByTestId("medical-role-current")).toContainText(en["medical.roles.revoked"]);
    await expect(panel.getByRole("region", { name: en["medical.roles.history"] })).toContainText("Synthetic disabled module revocation");
    await page.screenshot({ path: info.outputPath("disabled-module-revocation.png") });
  } finally { changeModule("enable-role-module"); }
});
