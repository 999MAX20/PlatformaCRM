import { openClinicalWorkspace } from "./clinical-card-navigation";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
let nextId = 7;
for (const language of ["ru", "kk", "en"] as const) for (const width of [1440, 390]) {
  const id = ++nextId;
  test(`order template ${language} ${width}: preview apply and retain provenance`, async ({ page, browser }, info) => {
    test.setTimeout(120_000);
    const t = { ru, kk, en }[language];
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
    await page.locator('form button[type="submit"]').click();
    const token = (await (await login).json()).access;
    await me;
    const base = process.env.E2E_API_BASE_URL!;
    const headContext = await browser.newContext();
    let head: string;
    try {
      const headPage = await headContext.newPage();
      await headPage.goto(`${process.env.E2E_BASE_URL}/login`);
      await headPage.locator('input[name="email"]').fill("medical-template-head@example.test");
      await headPage.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const headLogin = headPage.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await headPage.locator('form button[type="submit"]').click();
      const response = await headLogin; expect(response.ok()).toBe(true);
      head = (await response.json()).access;
    } finally { await headContext.close(); }
    const appointment = await (await page.request.get(`${base}/api/appointments/${id}/`, { headers: { Authorization: `Bearer ${token}` } })).json();
    const business_id = appointment.business;
    const common = width === 1440;
    const path = common ? "common/" : "";
    const title = `Synthetic order template ${id}`;
    async function templateCommand(suffix: string, data: object, actor: string) {
      const response = await page.request.post(`${base}/api/medical/document-templates/${suffix}`, {
        headers: { Authorization: `Bearer ${actor}`, "Idempotency-Key": crypto.randomUUID() }, data });
      expect(response.ok(), await response.text()).toBe(true); return response.json();
    }
    const template = await templateCommand(path, { business_id, title,
      text: "Synthetic approved instruction for {{patient.full_name}} / {{record.number}}", reason: "" }, common ? head : token);
    await templateCommand(`${path}versions/${template.version_id}/submit/`, { business_id }, common ? head : token);
    await templateCommand(`versions/${template.version_id}/decision/`, { business_id, decision: "approved", reason: "Synthetic review" }, head);
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}`);
    await openClinicalWorkspace(page);
    const workspace = page.getByTestId("clinical-workspace");
    await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`OT-${id}`);
    await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
    await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
    await expect(workspace.getByRole("textbox", { name: t["medical.clinical.complaints"], exact: true })).toBeVisible();
    await workspace.getByRole("tab", { name: t["medical.orders.title"], exact: true }).click();
    const orders = workspace.getByTestId("medical-orders");
    await orders.getByRole("button", { name: t["medical.orders.create"], exact: true }).click();
    const editor = page.getByTestId("medical-order-editor");
    await editor.getByLabel(t["medical.orders.kind"], { exact: true }).click();
    await page.getByRole("option", { name: t["medical.orders.medication"], exact: true }).click();
    await editor.getByLabel(t["medical.orders.field.dose"], { exact: true }).fill("Manually entered synthetic dose");
    const text = editor.getByRole("textbox", { name: t["medical.orders.text"], exact: true });
    await text.fill("Retain until confirmed");
    await editor.getByRole("button", { name: t["medical.documents.chooseTemplate"], exact: true }).click();
    const picker = page.getByTestId("order-template-picker");
    const search = picker.getByRole("form", { name: t["medical.templates.search"], exact: true });
    await search.getByLabel(t["medical.templates.searchText"], { exact: true }).fill("No matching synthetic template");
    await search.getByRole("button", { name: t["medical.templates.search"], exact: true }).click();
    await expect(picker.getByRole("status")).toHaveText(t["medical.templates.noMatches"]);
    await search.getByLabel(t["medical.templates.searchText"], { exact: true }).fill(title);
    await search.getByRole("button", { name: t["medical.templates.search"], exact: true }).click();
    await expect(picker.getByRole("button", { name: new RegExp(title) })).toBeVisible();
    await picker.screenshot({ path: info.outputPath("order-template-picker.png") });
    let failPreview = language === "ru" && width === 1440;
    await page.route("**/api/medical/orders/preview/**", route => {
      if (failPreview) return route.fulfill({ status: 503, contentType: "application/json", body: '{"code":"service_unavailable"}' });
      return route.continue();
    });
    await picker.getByRole("button", { name: new RegExp(title) }).click();
    if (failPreview) {
      await expect(picker.getByRole("alert")).toBeVisible(); failPreview = false;
      await picker.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(picker.getByRole("textbox", { name: t["medical.orders.text"], exact: true })).toHaveValue(new RegExp(`^Synthetic approved instruction for .+ / OT-${id}$`));
    await picker.screenshot({ path: info.outputPath("order-template-preview.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="order-template-picker"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    page.once("dialog", dialog => dialog.dismiss());
    await picker.getByRole("button", { name: t["medical.orders.applyTemplate"], exact: true }).click();
    await expect(picker).toBeVisible();
    page.once("dialog", dialog => dialog.accept());
    await picker.getByRole("button", { name: t["medical.orders.applyTemplate"], exact: true }).click();
    await expect(picker).not.toBeVisible();
    await expect(editor.getByRole("button", { name: t["medical.documents.chooseTemplate"], exact: true })).toBeFocused();
    await expect(text).toHaveValue(new RegExp(` / OT-${id}$`));
    await expect(editor.getByLabel(t["medical.orders.field.dose"], { exact: true })).toHaveValue("Manually entered synthetic dose");
    await text.fill((await text.inputValue()) + " — physician edit");
    await expect(editor.getByTestId("order-template-source")).toContainText(title);
    await editor.screenshot({ path: info.outputPath("order-template-applied.png") });
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor).not.toBeVisible();
    await expect(orders.getByTestId("order-template-source")).toContainText(title);
    await templateCommand(`${template.id}/availability/`, { business_id, is_active: false,
      expected_revision: 0, reason: "Synthetic pause", }, head);
    await orders.getByRole("button", { name: t["common.edit"], exact: true }).click();
    await text.fill("Later manual correction");
    await editor.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
    await expect(editor).not.toBeVisible();
    await orders.getByRole("button", { name: t["medical.orders.history"], exact: true }).click();
    const history = page.getByTestId("medical-order-history");
    await expect(history.getByTestId("order-template-source")).toHaveCount(2);
    await expect(history).toContainText("physician edit");
    await expect(history).toContainText("Later manual correction");
    await history.screenshot({ path: info.outputPath("order-template-history.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (language === "en" && width === 390) {
      await page.keyboard.press("Escape");
      await templateCommand(`${template.id}/availability/`, { business_id, is_active: true,
        expected_revision: 1, reason: "Synthetic resume" }, head);
      await orders.getByRole("button", { name: t["common.edit"], exact: true }).click();
      await editor.getByRole("button", { name: t["medical.documents.chooseTemplate"], exact: true }).click();
      await page.route("**/api/medical/orders/preview/**", route => route.fulfill({ status: 403,
        contentType: "application/json", body: '{"code":"permission_denied"}' }));
      await picker.getByRole("button", { name: new RegExp(title) }).click();
      await expect(editor).not.toBeVisible();
      await expect(picker).not.toBeVisible();
      await expect(orders.getByRole("alert")).toBeVisible();
      await expect(orders.getByTestId("order-template-source")).toHaveCount(0);
      await orders.screenshot({ path: info.outputPath("order-template-denied.png") });
    }
  });
}
