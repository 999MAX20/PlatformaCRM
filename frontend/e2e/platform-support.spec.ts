import { expect, test, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
test.beforeEach(() => test.skip(process.env.E2E_PLATFORM_SUPPORT !== "1", "Use scripts/verify_platform_support.py for disposable fixtures"));

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const pending = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  await expect(page).toHaveURL(/\/(app|platform)/);
  return { Authorization: `Bearer ${(await response.json()).access}` };
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
}

test("support clinic request reaches team and public reply while private notes stay private", async ({ page, browser, baseURL }, info) => {
  test.setTimeout(120_000);
  await login(page, `support-employee-${info.project.name}@example.com`);
  await page.goto("/app/support");
  await expect(page.getByText(ru["supportCases.empty"], { exact: true })).toBeVisible();
  await page.getByRole("button", { name: ru["supportCases.create"], exact: true }).click();
  await page.getByLabel(ru["supportCases.subject"], { exact: true }).fill(`Clinic question ${info.project.name}`);
  await page.getByRole("textbox", { name: ru["supportCases.description"], exact: true }).fill("Please check the settings");
  await page.getByRole("button", { name: ru["supportCases.submit"], exact: true }).click();
  await expect(page.getByTestId("support-case-detail")).toBeVisible();
  const id = Number(page.url().split("/").pop());
  const team = await browser.newPage({ baseURL, viewport: page.viewportSize() || undefined });
  try {
    await login(team, `support-team-${info.project.name}@example.com`);
    await team.goto(`/platform/support/${id}`);
    await team.getByRole("textbox", { name: ru["supportCases.internalText"], exact: true }).fill("PRIVATE SUPPORT NOTE");
    await team.getByRole("button", { name: ru["supportCases.saveNote"], exact: true }).click();
    await expect(team.getByTestId("support-internal-notes").getByText("PRIVATE SUPPORT NOTE", { exact: true })).toBeVisible();
    await team.getByRole("textbox", { name: ru["supportCases.replyClinic"], exact: true }).fill("The setting has been checked");
    await team.getByRole("button", { name: ru["supportCases.sendReply"], exact: true }).click();
    await expect(team.getByTestId("support-public-thread").getByText("The setting has been checked", { exact: true })).toBeVisible();
    await team.getByRole("button", { name: ru["supportCases.action.resolved"], exact: true }).click();
    await team.getByRole("textbox", { name: ru["supportCases.outcome"], exact: true }).fill("Configuration corrected");
    await team.getByTestId("support-action-dialog").getByRole("button", { name: ru["common.save"], exact: true }).click();
    await expect(team.getByTestId("support-action-dialog")).toBeHidden();
    await page.reload();
    await expect(page.getByTestId("support-public-thread").getByText("The setting has been checked", { exact: true })).toBeVisible();
    await expect(page.getByText("PRIVATE SUPPORT NOTE")).toHaveCount(0);
    await expect(page.getByTestId("support-internal-notes")).toHaveCount(0);
    await page.getByRole("button", { name: ru["supportCases.reopen"], exact: true }).click();
    await page.getByRole("textbox", { name: ru["supportCases.reason"], exact: true }).fill("The issue returned");
    await page.getByTestId("support-action-dialog").getByRole("button", { name: ru["common.save"], exact: true }).click();
    await expect(page.getByTestId("support-case-history")).toContainText("The issue returned");
    await noOverflow(page); await noOverflow(team);
    await page.screenshot({ path: info.outputPath("support-clinic.png"), fullPage: true });
    await team.screenshot({ path: info.outputPath("support-team.png"), fullPage: true });
  } finally { await team.close(); }
});

test("support team creates cases and resolves stale version without losing the draft", async ({ page }, info) => {
  test.setTimeout(120_000);
  const headers = await login(page, `support-team-${info.project.name}@example.com`);
  await page.goto(`/platform/support?search=Queue%20fixture%20${info.project.name}&page_size=10`);
  await expect(page.getByTestId("support-case-row")).toHaveCount(10);
  await page.getByRole("button", { name: ru["pagination.next"], exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByTestId("support-case-row").first().getByRole("link").click();
  await page.getByRole("link", { name: ru["supportCases.back"], exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByRole("button", { name: ru["supportCases.create"], exact: true }).click();
  const dialog = page.getByTestId("support-create-dialog");
  await dialog.getByLabel(ru["supportCases.clinicSearch"], { exact: true }).fill(`Support Clinic ${info.project.name}`);
  await dialog.getByRole("combobox", { name: new RegExp(ru["supportCases.clinic"]) }).click();
  await page.getByRole("option", { name: `Support Clinic ${info.project.name}`, exact: true }).click();
  await dialog.getByLabel(ru["supportCases.subject"], { exact: true }).fill(`Team question ${info.project.name}`);
  await dialog.getByRole("textbox", { name: ru["supportCases.description"], exact: true }).fill("We are following up");
  await dialog.getByRole("button", { name: ru["supportCases.submit"], exact: true }).click();
  await expect(page.getByTestId("support-case-detail")).toBeVisible();
  const id = Number(page.url().split("/").pop());
  await page.getByRole("button", { name: ru["supportCases.assign"], exact: true }).click();
  await page.getByTestId("support-action-dialog").getByRole("combobox").click();
  await page.getByRole("option", { name: `Support team ${info.project.name}`, exact: true }).click();
  await page.getByTestId("support-action-dialog").getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(page.getByTestId("support-action-dialog")).toBeHidden();
  await page.getByRole("button", { name: ru["supportCases.action.resolved"], exact: true }).click();
  await page.getByRole("textbox", { name: ru["supportCases.outcome"], exact: true }).fill("Preserved resolution draft");
  const current = await page.request.get(`${api}/api/platform/support-cases/${id}/`, { headers });
  const changed = await page.request.post(`${api}/api/platform/support-cases/${id}/assign/`, { headers, data: { assigned_to: null, version: (await current.json()).version } });
  expect(changed.ok()).toBeTruthy();
  await page.getByTestId("support-action-dialog").getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(page.getByRole("button", { name: ru["supportCases.refreshVersion"], exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: ru["supportCases.outcome"], exact: true })).toHaveValue("Preserved resolution draft");
  await page.getByRole("button", { name: ru["supportCases.refreshVersion"], exact: true }).click();
  await page.getByTestId("support-action-dialog").getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(page.getByTestId("support-action-dialog")).toBeHidden();
  await expect(page.getByTestId("support-case-history")).toContainText("Preserved resolution draft");
  await noOverflow(page);
});

test("support handles recovery permissions draft protection and all locales", async ({ page }, info) => {
  test.setTimeout(120_000);
  await login(page, `support-owner-${info.project.name}@example.com`);
  await page.route("**/api/support/cases/?*", async route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "temporary_service_failure", category: "temporary", detail: "Temporary failure" }) }));
  const listFailure = page.waitForResponse(response => /\/api\/support\/cases\/\?/.test(response.url()) && response.status() === 503);
  await page.goto("/app/support");
  await listFailure;
  await expect(page.getByTestId("support-list").getByTestId("inline-fallback")).toBeVisible();
  await expect(page.getByTestId("support-case-row")).toHaveCount(0);
  await page.unroute("**/api/support/cases/?*");
  await page.getByTestId("support-list").getByRole("button", { name: ru["common.refresh"], exact: true }).first().click();
  await expect(page.getByTestId("support-case-row").first()).toBeVisible();
  await page.getByTestId("support-case-row").first().getByRole("link").click();
  const draft = page.getByRole("textbox", { name: ru["supportCases.replySupport"], exact: true });
  await draft.fill("Keep this draft");
  const detailRoute = /\/api\/support\/cases\/\d+\/\?business=/;
  await page.route(detailRoute, route => route.fulfill({ status: 503, contentType: "application/json", body: '{"code":"temporary_service_failure"}' }));
  const refreshFailure = page.waitForResponse(response => detailRoute.test(response.url()) && response.status() === 503);
  await page.getByTestId("support-case-detail").getByRole("button", { name: ru["common.refresh"], exact: true }).click();
  await refreshFailure;
  await expect(page.getByTestId("support-case-detail").getByTestId("inline-fallback")).toBeVisible();
  await expect(draft).toHaveValue("Keep this draft");
  await page.unroute(detailRoute);
  await page.route("**/api/support/cases/*/messages/?*", async route => route.request().method() === "POST" ? route.fulfill({ status: 503, contentType: "application/json", body: '{"code":"temporary_service_failure","category":"temporary"}' }) : route.continue());
  const sendFailure = page.waitForResponse(response => response.request().method() === "POST" && response.url().includes("/messages/") && response.status() === 503);
  await page.getByRole("button", { name: ru["supportCases.sendReply"], exact: true }).click();
  await sendFailure;
  await expect(draft).toHaveValue("Keep this draft");
  await page.getByRole("link", { name: ru["supportCases.back"], exact: true }).click();
  await page.getByRole("button", { name: ru["taskWorkspace.keepEditing"], exact: true }).click();
  await expect(draft).toHaveValue("Keep this draft");
  await page.unroute("**/api/support/cases/*/messages/?*");
  await page.getByRole("button", { name: ru["supportCases.sendReply"], exact: true }).click();
  await expect(draft).toHaveValue("");
  for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.reload();
    await expect(page.getByRole("heading", { name: copy["supportCases.publicThread"], exact: true })).toBeVisible();
    await page.getByRole("textbox", { name: copy["supportCases.replySupport"], exact: true }).focus();
    await expect(page.getByRole("textbox", { name: copy["supportCases.replySupport"], exact: true })).toBeFocused();
    await noOverflow(page);
  }
  await page.route("**/api/support/cases/*/?*", async route => route.fulfill({ status: 403, contentType: "application/json", body: '{"code":"permission_denied","category":"permission"}' }));
  await page.reload();
  await expect(page.getByTestId("permission-fallback")).toBeVisible();
  await expect(page.getByTestId("support-public-thread")).toHaveCount(0);
});
