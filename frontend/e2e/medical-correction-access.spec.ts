import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
async function login(page: Page, email: string, language: string) {
  await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const authenticated = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await authenticated).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  return { Authorization: `Bearer ${token}` };
}

for (const language of ["ru", "kk", "en"] as const) for (const width of [1440, 390]) {
  test(`correction history ${language} ${width}: actors, target and expiry`, async ({ page }, info) => {
    const t = { ru, kk, en }[language];
    await page.setViewportSize({ width, height: 1000 });
    const headers = await login(page, "source-head@example.test", language);
    const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers, params: { q: "Synthetic patient" } });
    const client = (await clients.json()).results.find((item: { full_name: string }) => item.full_name === "Synthetic patient");
    await page.goto(`/app/clients/${client.id}`);
    await page.getByTestId("patient-administration").getByLabel(t["medical.branch"], { exact: true }).click();
    await page.getByRole("option", { name: "First", exact: true }).click();
    const panel = page.getByTestId("correction-access");
    await panel.getByLabel(t["medical.correctionAccess.scope"], { exact: true }).click();
    await page.getByRole("option", { name: t["medical.correctionAccess.reviewQueue"], exact: true }).click();
    const row = panel.locator("li").filter({ hasText: t["medical.correctionAccess.completed"] }).first();
    await expect(row.getByText(t["medical.correctionAccess.requestedBy"], { exact: false })).toBeVisible();
    await expect(row.getByText(t["medical.correctionAccess.reviewedBy"], { exact: false })).toBeVisible();
    await expect(row.getByText(t["medical.correctionAccess.until"], { exact: false })).toBeVisible();
    expect((await new AxeBuilder({ page }).include('[data-testid="correction-access"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await row.evaluate(element => element.scrollIntoView({ block: "center" }));
    await row.screenshot({ path: info.outputPath("history.png") });
  });
}

for (const width of [1440, 390]) test(`correction recovery ${width}: retain draft, retry and clear denied data`, async ({ page }, info) => {
  const t = ru;
  await page.setViewportSize({ width, height: 1000 });
  const headers = await login(page, "medical-role-doctor@example.test", "ru");
  const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers, params: { q: "Synthetic patient" } });
  const client = (await clients.json()).results.find((item: { full_name: string }) => item.full_name === "Synthetic patient");
  await page.goto(`/app/clients/${client.id}`);
  await page.getByTestId("patient-administration").getByLabel(t["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  const panel = page.getByTestId("correction-access");
  await panel.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true }).click();
  let dialog = page.getByRole("dialog");
  await dialog.getByLabel(t["medical.correctionAccess.encounter"], { exact: true }).click();
  await page.getByRole("option").nth(1).click();
  await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic retained reason");
  let fail = true;
  await page.route(url => url.pathname === "/api/medical/correction-access/", route => {
    if (fail && route.request().method() === "POST") { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
    return route.continue();
  });
  let response = page.waitForResponse(r => r.url().endsWith("/api/medical/correction-access/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true }).click();
  expect((await response).status()).toBe(503);
  await expect(dialog.getByRole("textbox", { name: t["medical.reason"], exact: true })).toHaveValue("Synthetic retained reason");
  await dialog.screenshot({ path: info.outputPath("request-retry.png") });
  response = page.waitForResponse(r => r.url().endsWith("/api/medical/correction-access/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true }).click();
  const created = await response; expect(created.status()).toBe(201);
  const item = await created.json();
  await expect(dialog).toHaveCount(0);
  await page.getByTestId(`correction-access-${item.id}`).getByRole("button", { name: t["medical.correctionAccess.withdraw"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic withdrawal");
  await dialog.getByRole("button", { name: t["medical.correctionAccess.withdraw"], exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.unrouteAll({ behavior: "wait" });
  await page.route(url => url.pathname === "/api/medical/correction-access/", route => route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
  await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(panel.getByRole("button", { name: t["common.retry"], exact: true })).toBeVisible();
  await expect(panel.locator("li")).toHaveCount(0);
  await expect(panel.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true })).toHaveCount(0);
  await panel.screenshot({ path: info.outputPath("denied-cleared.png") });
});

for (const language of ["ru", "kk", "en"] as const) for (const width of [1440, 390]) {
  test(`correction access ${language} ${width}: request, approve, edit and finish`, async ({ page, browser }, info) => {
    const t = { ru, kk, en }[language];
    await page.setViewportSize({ width, height: 1000 });
    const headers = await login(page, "medical-role-doctor@example.test", language);
    const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers, params: { q: "Synthetic patient" } });
    expect(clients.status()).toBe(200);
    const client = (await clients.json()).results.find((item: { full_name: string }) => item.full_name === "Synthetic patient");
    await page.goto(`/app/clients/${client.id}`);
    await page.getByTestId("patient-administration").getByLabel(t["medical.branch"], { exact: true }).click();
    await page.getByRole("option", { name: "First", exact: true }).click();
    const panel = page.getByTestId("correction-access");
    const opener = panel.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true });
    await opener.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape"); await expect(opener).toBeFocused();
    await opener.click();
    let dialog = page.getByRole("dialog");
    await dialog.getByLabel(t["medical.correctionAccess.encounter"], { exact: true }).click();
    await page.getByRole("option").nth(1).click();
    const document = language === "en" && width === 390;
    if (document) {
      await dialog.getByLabel(t["medical.correctionAccess.target"], { exact: true }).click();
      await page.getByRole("option").nth(1).click();
    }
    await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic browser correction");
    await dialog.screenshot({ path: info.outputPath("request.png") });
    const requested = page.waitForResponse(r => r.url().endsWith("/api/medical/correction-access/") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: t["medical.correctionAccess.request"], exact: true }).click();
    const response = await requested; expect(response.status()).toBe(201);
    const item = await response.json();
    await expect(dialog).toHaveCount(0);
    const headContext = await browser.newContext({ baseURL: process.env.E2E_BASE_URL, viewport: { width, height: 1000 } });
    try {
      const head = await headContext.newPage();
      await login(head, "source-head@example.test", language);
      await head.goto(`/app/clients/${client.id}`);
      await head.getByTestId("patient-administration").getByLabel(t["medical.branch"], { exact: true }).click();
      await head.getByRole("option", { name: "First", exact: true }).click();
      const review = head.getByTestId("correction-access");
      await review.getByLabel(t["medical.correctionAccess.scope"], { exact: true }).click();
      await head.getByRole("option", { name: t["medical.correctionAccess.reviewQueue"], exact: true }).click();
      await head.getByTestId(`correction-access-${item.id}`).getByRole("button", { name: t["medical.correctionAccess.approve"], exact: true }).click();
      const headDialog = head.getByRole("dialog");
      await headDialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic head approval");
      await headDialog.getByRole("button", { name: t["medical.correctionAccess.approve"], exact: true }).click();
      await expect(headDialog).toHaveCount(0);
      const approvedRow = head.getByTestId(`correction-access-${item.id}`);
      await expect(approvedRow.getByText(t["medical.correctionAccess.active"], { exact: false })).toBeVisible();
      await approvedRow.screenshot({ path: info.outputPath("approved.png") });
    } finally { await headContext.close(); }
    await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
    const row = page.getByTestId(`correction-access-${item.id}`);
    await row.getByRole("button", { name: t["medical.correctionAccess.edit"], exact: true }).click();
    dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: document ? t["medical.correctionAccess.document"] : t["medical.clinical.plan"], exact: true }).fill(`Synthetic correction ${language} ${width}`);
    if (!document) {
      await dialog.getByRole("textbox", { name: t["medical.clinical.allergies"], exact: true }).fill(`Synthetic corrected allergy ${language}`);
      await dialog.getByRole("textbox", { name: t["medical.clinical.contraindications"], exact: true }).fill("Synthetic corrected contraindication");
      await dialog.getByTestId("clinical-plan-steps").getByRole("button", { name: t["medical.plan.addStep"], exact: true }).click();
      await dialog.getByTestId("clinical-plan-steps").getByRole("textbox").last().fill("Synthetic corrected plan step");
      const procedureLabel = t["medical.clinical.procedures"];
      await dialog.getByRole("checkbox", { name: t["medical.clinical.notApplicableFor"].replace("{field}", procedureLabel), exact: true }).check();
      await dialog.getByRole("textbox", { name: t["medical.clinical.notApplicableReason"].replace("{field}", procedureLabel), exact: true }).fill("Synthetic correction consultation only");
    }
    await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic draft correction");
    expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await dialog.screenshot({ path: info.outputPath("edit.png") });
    await dialog.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    if (!document) {
      await row.getByRole("button", { name: t["medical.correctionAccess.edit"], exact: true }).click();
      dialog = page.getByRole("dialog");
      await expect(dialog.getByRole("textbox", { name: t["medical.clinical.allergies"], exact: true })).toHaveValue(`Synthetic corrected allergy ${language}`);
      await expect(dialog.getByRole("textbox", { name: t["medical.clinical.contraindications"], exact: true })).toHaveValue("Synthetic corrected contraindication");
      await expect(dialog.getByTestId("clinical-plan-steps").getByRole("textbox").last()).toHaveValue("Synthetic corrected plan step");
      await dialog.getByTestId("clinical-plan-steps").screenshot({ path: info.outputPath("corrected-plan-steps.png") });
      await expect(dialog.getByRole("textbox", { name: t["medical.clinical.notApplicableReason"].replace("{field}", t["medical.clinical.procedures"]), exact: true })).toHaveValue("Synthetic correction consultation only");
      await dialog.getByRole("textbox", { name: t["medical.clinical.notApplicableReason"].replace("{field}", t["medical.clinical.procedures"]), exact: true }).locator("../..").screenshot({ path: info.outputPath("corrected-not-applicable.png") });
      await dialog.getByRole("textbox", { name: t["medical.clinical.allergies"], exact: true }).locator("..").screenshot({ path: info.outputPath("corrected-allergies.png") });
      await page.keyboard.press("Escape");
      await expect(dialog).toHaveCount(0);
    }
    await row.getByRole("button", { name: t["medical.correctionAccess.complete"], exact: true }).click();
    dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic completed");
    await dialog.getByRole("button", { name: t["medical.correctionAccess.complete"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(row.getByText(t["medical.correctionAccess.completed"], { exact: false })).toBeVisible();
    await expect(row.getByRole("button")).toHaveCount(0);
  });
}
