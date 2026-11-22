import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.use({ actionTimeout: 15_000 });
async function login(page: Page, language: string) {
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const authentication = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await authentication).json()).access as string;
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/settings#medical-templates");
  return token;
}

test("templates: stale version and permission denial clear private state", async ({ page }, info) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });
  const token = await login(page, "en");
  const t = en;
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/document-templates/`;
  const headers = { Authorization: `Bearer ${token}`, "Idempotency-Key": "synthetic-conflict-template" };
  const payload = { business_id: 1, title: "Synthetic concurrent template", text: "First", reason: "" };
  const created = await page.request.post(root, { headers, data: payload });
  expect(created.ok()).toBe(true);
  const source = await created.json();
  const workspace = page.getByTestId("medical-template-workspace");
  await workspace.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  const row = workspace.getByRole("listitem").filter({ hasText: payload.title });
  await row.getByRole("button").click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: t["medical.templates.edit"], exact: true }).click();
  await dialog.getByRole("textbox", { name: t["medical.templates.text"], exact: true }).fill("Synthetic unsaved private text");
  const updated = await page.request.post(root + source.id + "/draft/", { headers: { ...headers, "Idempotency-Key": "synthetic-competing-edit" },
    data: { ...payload, text: "Concurrent saved text", expected_revision: 1 } });
  expect(updated.ok()).toBe(true);
  await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
  await expect(dialog.getByRole("textbox", { name: t["medical.templates.text"], exact: true })).toHaveValue("Synthetic unsaved private text");
  await page.screenshot({ path: info.outputPath("conflict.png") });
  page.once("dialog", confirmation => confirmation.accept());
  await dialog.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await row.getByRole("button").click();
  await expect(dialog.getByText("Concurrent saved text", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: t["medical.templates.edit"], exact: true }).click();
  await dialog.getByRole("textbox", { name: t["medical.templates.text"], exact: true }).fill("Synthetic revoked private text");
  await page.route("**/api/medical/document-templates/*/draft/", route => route.fulfill({ status: 403, json: { detail: "Synthetic access revoked" } }));
  await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(workspace.getByRole("listitem")).toHaveCount(0);
  await expect(page.getByText("Synthetic revoked private text")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("denied.png") });
});

test("templates: list and history pagination, read recovery and navigation", async ({ page }, info) => {
  test.setTimeout(120_000);
  const token = await login(page, "en");
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/document-templates/`;
  const headers = { Authorization: `Bearer ${token}` };
  let first: { id: number; version_id: number } | null = null;
  for (let index = 0; index < 21; index++) {
    const response = await page.request.post(root, { headers: { ...headers, "Idempotency-Key": `synthetic-page-${index}` },
      data: { business_id: 1, title: `Synthetic pagination ${index}`, text: "Synthetic initial text", reason: "" } });
    expect(response.ok()).toBe(true);
    if (index === 0) first = await response.json();
  }
  for (let revision = 1; revision <= 20; revision++) {
    const response = await page.request.post(root + first!.id + "/draft/", { headers: { ...headers, "Idempotency-Key": `synthetic-history-${revision}` },
      data: { business_id: 1, title: "Synthetic pagination 0", text: `Synthetic text ${revision + 1}`, reason: "", expected_revision: revision } });
    expect(response.ok()).toBe(true);
  }
  const workspace = page.getByTestId("medical-template-workspace");
  await workspace.getByRole("button", { name: en["medical.clinical.reload"], exact: true }).click();
  await expect(workspace.getByRole("listitem")).toHaveCount(20);
  await workspace.getByRole("button", { name: en["medical.templates.more"], exact: true }).click();
  const row = workspace.getByRole("listitem").filter({ has: page.getByText("Synthetic pagination 0", { exact: true }) });
  await expect(row).toBeVisible();
  let failRead = true;
  await page.route(/\/api\/medical\/document-templates\/versions\/\d+\/(?:\?|$)/, route => {
    if (failRead && route.request().method() === "GET") return route.fulfill({ status: 503, json: { detail: "Synthetic read outage" } });
    return route.continue();
  });
  await row.getByRole("button").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toBeVisible();
  failRead = false;
  await dialog.getByRole("button", { name: en["common.retry"], exact: true }).click();
  await expect(dialog.getByText("Synthetic text 21", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: en["medical.templates.more"], exact: true }).click();
  await dialog.getByRole("button", { name: "Version 1", exact: true }).click();
  await expect(dialog.getByText("Synthetic initial text", { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("desktop-sidebar").getByRole("link", { name: en["nav.settings"], exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("pagination.png") });
});

for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  test(`templates ${language} ${mobile ? "mobile" : "desktop"}: create, edit, history and safe retry`, async ({ page }, info) => {
    test.setTimeout(120_000);
    const t = { ru, kk, en }[language];
    await page.setViewportSize(mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 });
    await login(page, language);
    const workspace = page.getByTestId("medical-template-workspace");
    await workspace.getByRole("button", { name: t["medical.templates.create"], exact: true }).click();
    const dialog = page.getByRole("dialog");
    const title = `Synthetic template ${language} ${mobile}`;
    await dialog.getByRole("textbox", { name: t["medical.templates.title"], exact: true }).fill(title);
    await dialog.getByRole("textbox", { name: t["medical.templates.text"], exact: true }).fill("Synthetic version one\nLiteral <script> & {{patient}}");
    page.once("dialog", confirmation => confirmation.dismiss());
    await page.keyboard.press("Escape");
    await expect(dialog.getByRole("textbox", { name: t["medical.templates.title"], exact: true })).toHaveValue(title);
    const keys: string[] = [];
    await page.route("**/api/medical/document-templates/", async route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      if (keys.length === 1) return route.fulfill({ status: 503, json: { detail: "Synthetic outage" } });
      return route.continue();
    });
    await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(dialog.getByRole("textbox", { name: t["medical.templates.title"], exact: true })).toHaveValue(title);
    await page.screenshot({ path: info.outputPath("editor-recovery.png") });
    await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    expect(keys[0]).toBe(keys[1]);
    const row = workspace.getByRole("listitem").filter({ hasText: title });
    await row.getByRole("button").click();
    await expect(dialog.getByText("Synthetic version one", { exact: false })).toBeVisible();
    await dialog.getByRole("button", { name: t["medical.templates.edit"], exact: true }).click();
    await dialog.getByRole("textbox", { name: t["medical.templates.text"], exact: true }).fill("Synthetic version two");
    await dialog.getByRole("textbox", { name: t["medical.templates.reason"], exact: true }).fill("Synthetic correction");
    await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await row.getByRole("button").click();
    await expect(dialog.getByText("Synthetic version two", { exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: t["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
    await expect(dialog.getByText("Synthetic version one", { exact: false })).toBeVisible();
    await expect(dialog.getByRole("button", { name: t["medical.templates.edit"], exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const audit = await new AxeBuilder({ page }).include('[role="dialog"]').analyze();
    expect(audit.violations.filter(item => ["critical", "serious"].includes(item.impact ?? ""))).toEqual([]);
    await page.screenshot({ path: info.outputPath("history.png") });
    await page.keyboard.press("Escape");
    await expect(row.getByRole("button")).toBeFocused();
    await page.screenshot({ path: info.outputPath("list.png") });
  });
}
