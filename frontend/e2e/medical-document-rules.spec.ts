import { test, expect } from "@playwright/test";
import { ru as t } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test("document rules: head creates versions with retained retry and mobile history", async ({ page }, info) => {
  test.setTimeout(120_000);
  const marker = crypto.randomUUID().slice(0, 8);
  const title = `Synthetic rules template ${marker}`;
  const name = `Synthetic document kind ${marker}`;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-template-head@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const authentication = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const headers = { Authorization: `Bearer ${(await (await authentication).json()).access}` };
  await expect(page).toHaveURL(/\/app\//);
  const command = async (path: string, data: object) => {
    const response = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/document-templates/${path}`, {
      headers: { ...headers, "Idempotency-Key": crypto.randomUUID() }, data });
    expect(response.ok(), await response.text()).toBe(true); return response.json();
  };
  const template = await command("common/", { business_id: 1, title, text: "Synthetic text", reason: "" });
  await command(`common/versions/${template.version_id}/submit/`, { business_id: 1 });
  await command(`versions/${template.version_id}/decision/`, { business_id: 1, decision: "approved", reason: "" });
  await page.goto("/app/settings#medical-templates");
  const workspace = page.getByTestId("medical-template-workspace");
  await workspace.getByRole("button", { name: t["medical.rules.title"], exact: true }).click();
  const rules = page.getByTestId("document-rules");
  await rules.getByRole("button", { name: t["medical.rules.create"], exact: true }).click();
  const form = rules.getByTestId("medical-role-command");
  await form.getByLabel(t["medical.rules.name"], { exact: true }).fill(name);
  await form.getByLabel(t["medical.rules.docx"], { exact: true }).check();
  await form.getByRole("button", { name: t["medical.rules.selectTemplates"], exact: true }).click();
  await form.getByLabel(t["medical.rules.searchTemplates"], { exact: true }).fill(marker);
  await form.getByLabel(t["medical.rules.searchTemplates"], { exact: true }).press("Enter");
  await form.getByRole("button", { name: title, exact: true }).click();
  await form.getByRole("button", { name: t["medical.rules.selectTemplates"], exact: true }).click();
  await form.getByRole("combobox", { name: `${t["medical.rules.moment"]} ${t["medical.rules.moment.optional"]}`, exact: true }).click();
  await page.getByRole("option", { name: t["medical.rules.moment.before_completion"], exact: true }).click();
  await form.getByRole("combobox", { name: new RegExp(`^${t["medical.fields.choose"]} `) }).click();
  await page.getByRole("option", { name: t["medical.fullName"], exact: true }).click();
  await form.getByRole("button", { name: t["medical.rules.addField"], exact: true }).click();
  const signerSelect = form.getByRole("combobox", { name: new RegExp(`^${t["medical.rules.signer"]} `) });
  for (const role of ["medical_head", "primary_clinician"] as const) {
    await signerSelect.click();
    await page.getByRole("option", { name: t[`medical.rules.role.${role}`], exact: true }).click();
    await form.getByRole("button", { name: t["medical.rules.addSigner"], exact: true }).click();
  }
  await form.getByRole("button", { name: `${t["medical.rules.moveEarlier"]}: ${t["medical.rules.role.primary_clinician"]}`, exact: true }).click();
  await expect(form.getByRole("listitem").filter({ hasText: `1. ${t["medical.rules.role.primary_clinician"]}` })).toBeVisible();
  await form.getByRole("checkbox", { name: t["medical.rules.role.medical_head"], exact: true }).check();
  await form.getByRole("textbox", { name: t["medical.templates.reason"], exact: true }).fill("Synthetic first rule revision");
  page.once("dialog", dialog => dialog.dismiss());
  await rules.getByRole("button", { name: t["common.back"], exact: true }).click();
  await expect(form.getByLabel(t["medical.rules.name"], { exact: true })).toHaveValue(name);
  await rules.getByLabel(t["medical.rules.name"], { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("rules-editor-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await rules.getByLabel(t["medical.rules.name"], { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("rules-editor-mobile.png") });
  await form.getByRole("button", { name: t["medical.rules.selectTemplates"], exact: true })
    .evaluate(element => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("rules-template-choice-mobile.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await form.getByRole("combobox", { name: new RegExp(`^${t["medical.rules.signer"]} `) }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("rules-requirements-mobile.png") });
  let fail = true;
  const keys: string[] = [];
  await page.route("**/api/medical/document-kinds/", async route => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (fail) { fail = false; return route.fulfill({ status: 503, json: { detail: "Synthetic rule outage" } }); }
    return route.continue();
  });
  await form.getByRole("button", { name: t["common.save"], exact: true }).click();
  await expect(form.getByRole("alert")).toBeVisible();
  await expect(form.getByRole("textbox", { name: t["medical.templates.reason"], exact: true })).toHaveValue("Synthetic first rule revision");
  await form.getByRole("button", { name: t["common.save"], exact: true }).evaluate(element => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("rules-retry-mobile.png") });
  const saved = page.waitForResponse(response => response.url().endsWith("/api/medical/document-kinds/") && response.request().method() === "POST" && response.status() === 201);
  await form.getByRole("button", { name: t["common.save"], exact: true }).focus();
  await page.keyboard.press("Enter");
  const result = await (await saved).json();
  expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
  const row = rules.getByRole("listitem").filter({ hasText: name });
  await expect(row).toBeVisible();
  await expect(rules.getByRole("button", { name: t["medical.rules.create"], exact: true })).toBeFocused();
  await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
  const detail = rules.getByTestId("document-rule-detail");
  await expect(detail.getByText(title, { exact: true })).toBeVisible();
  await detail.getByRole("button", { name: t["medical.templates.newVersion"], exact: true }).click();
  await form.getByLabel(t["medical.rules.docx"], { exact: true }).uncheck();
  await form.getByRole("textbox", { name: t["medical.templates.reason"], exact: true }).fill("Synthetic disabled draft export");
  await form.getByRole("button", { name: t["common.save"], exact: true }).click();
  await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
  await expect(detail.getByText(t["medical.rules.docxDisabled"], { exact: true })).toBeVisible();
  await detail.getByRole("button", { name: t["medical.templates.version"].replace("{revision}", "1"), exact: true }).click();
  await expect(detail.getByText(t["medical.rules.docxEnabled"], { exact: true })).toBeVisible();
  await expect(detail.getByRole("button", { name: t["medical.templates.newVersion"], exact: true })).toHaveCount(0);
  await detail.getByRole("heading", { name, exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("rules-history-mobile.png") });
  const history = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/document-kinds/${result.kind_id}/history/?business_id=1`, { headers });
  expect(history.ok()).toBe(true);
  const versions = (await history.json()).results;
  expect(versions.map((item: { revision: number }) => item.revision)).toEqual([2, 1]);
  expect(versions[1].content.default.signers).toEqual(["primary_clinician", "medical_head"]);
  expect(versions[1].content.default.reviewers).toEqual(["primary_clinician", "medical_head"]);
  await rules.getByRole("button", { name: t["common.back"], exact: true }).click();
  await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
  await detail.getByRole("button", { name: t["medical.templates.newVersion"], exact: true }).click();
  await form.getByRole("textbox", { name: t["medical.templates.reason"], exact: true }).fill("Synthetic retained conflict input");
  const concurrent = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/document-kinds/${result.kind_id}/save/`, {
    headers: { ...headers, "Idempotency-Key": crypto.randomUUID() }, data: {
      business_id: 1, expected_revision: 2, reason: "Synthetic concurrent update", template_ids: [template.id],
      content: { name, docx_allowed: false, default: versions[0].content.default, services: [] },
    },
  });
  expect(concurrent.ok(), await concurrent.text()).toBe(true);
  await form.getByRole("button", { name: t["common.save"], exact: true }).click();
  await expect(form.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
  await expect(form.getByRole("textbox", { name: t["medical.templates.reason"], exact: true })).toHaveValue("Synthetic retained conflict input");
  await expect(form.getByRole("button", { name: t["common.save"], exact: true })).toBeDisabled();
  await form.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).evaluate(element => element.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.screenshot({ path: info.outputPath("rules-conflict-mobile.png") });
  page.once("dialog", dialog => dialog.accept());
  await form.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
  await expect(detail.getByText(t["medical.templates.version"].replace("{revision}", "3"), { exact: true }).first()).toBeVisible();
  await rules.getByRole("button", { name: t["common.back"], exact: true }).click();
  await page.route(`**/api/medical/document-kinds/${result.kind_id}/history/**`, route => route.fulfill({ status: 403, json: { detail: "Synthetic revoked access" } }));
  await row.getByRole("button", { name: t["medical.templates.open"], exact: true }).click();
  await expect(workspace.getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("document-rules")).toHaveCount(0);
  await expect(workspace.getByText(name, { exact: true })).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("rules-denied-mobile.png") });
});
