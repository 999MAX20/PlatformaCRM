import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
let sequence = 7;
for (const language of ["ru", "kk", "en"] as const) for (const mobile of [false, true]) {
  const id = ++sequence;
  test(`clinical visit link ${language} ${mobile ? "mobile" : "desktop"}: save, unlink and exact history`, async ({ page }, info) => {
    const t = { ru, kk, en }[language];
    await page.setViewportSize({ width: mobile ? 390 : 1440, height: 1000 });
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/login");
    await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
    await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
    const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
    await page.locator('form button[type="submit"]').click();
    const headers = { Authorization: `Bearer ${(await (await login).json()).access}` };
    await me;
    const api = process.env.E2E_API_BASE_URL!;
    const appointment = await (await page.request.get(`${api}/api/appointments/${id}/`, { headers })).json();
    const context = await (await page.request.get(`${api}/api/medical/encounters/appointment-context/`, {
      headers, params: { business_id: appointment.business, appointment_id: id },
    })).json();
    const scope = { business_id: context.business_id, patient_id: context.patient.id };
    const record = await page.request.post(`${api}/api/medical/records/`, { headers: { ...headers, "Idempotency-Key": `link-record-${id}` },
      data: { ...scope, appointment_id: id, expected_patient_revision: context.patient.revision, number: `LINK-${id}` } });
    expect(record.status()).toBe(201);
    const encounter = await page.request.post(`${api}/api/medical/encounters/`, { headers: { ...headers, "Idempotency-Key": `link-open-${id}` },
      data: { ...scope, appointment_id: id, record_id: (await record.json()).id,
        expected_patient_revision: context.patient.revision, expected_appointment_updated_at: context.appointment.updated_at } });
    expect(encounter.status()).toBe(201);
    await page.goto(`/app/calendar?appointment=${id}&date=${appointment.start_at.slice(0, 10)}`);
    const open = page.getByTestId("clinical-appointment-entry").getByRole("button", { name: t["medical.clinical.open"], exact: true });
    await open.click();
    const workspace = page.getByTestId("clinical-workspace");
    const steps = workspace.getByTestId("clinical-plan-steps");
    await steps.getByRole("button", { name: t["medical.plan.addStep"], exact: true }).click();
    await steps.getByRole("textbox").fill(`Synthetic linked plan ${id}`);
    const link = steps.getByTestId("clinical-visit-link");
    const teeth = steps.getByTestId("clinical-plan-teeth");
    for (const tooth of [11, 51]) {
      await teeth.getByRole("combobox").click();
      await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} ${tooth}`, exact: true }).click();
    }
    await teeth.getByRole("button", { name: t["medical.plan.removeTooth"].replace("{tooth}", "51"), exact: true }).click();
    await expect(teeth.getByRole("combobox")).toBeFocused();
    await teeth.getByRole("combobox").click();
    await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 51`, exact: true }).click();
    let fail = true;
    let empty = language === "ru" && !mobile;
    await page.route("**/api/medical/encounters/visit-steps/**", route => {
      if (empty) { empty = false; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ results: [], next_before_id: null }) }); }
      if (mobile && fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
      return route.continue();
    });
    await link.getByRole("button", { name: t["medical.plan.linkVisit"], exact: true }).click();
    if (language === "ru" && !mobile) {
      await expect(link.getByText(t["medical.plan.noVisitSteps"], { exact: true })).toBeVisible();
      await link.getByRole("button", { name: t["common.cancel"], exact: true }).click();
      await link.getByRole("button", { name: t["medical.plan.linkVisit"], exact: true }).click();
    }
    if (mobile) {
      await expect(link.getByRole("alert")).toBeVisible();
      await expect(steps.getByRole("textbox")).toHaveValue(`Synthetic linked plan ${id}`);
      await link.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await link.getByLabel(t["medical.plan.selectVisit"], { exact: true }).click();
    const options = page.getByRole("option").filter({ hasText: "Synthetic service" });
    await expect(options).toHaveCount(2);
    await page.screenshot({ path: info.outputPath("visit-step-picker.png") });
    const chosen = await options.first().innerText();
    await options.first().click();
    await link.getByRole("button", { name: t["medical.plan.applyVisit"], exact: true }).click();
    await expect(link.getByRole("button", { name: t["medical.plan.changeVisit"], exact: true })).toBeFocused();
    await expect(link).toContainText(chosen);
    const save = workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true });
    await save.click();
    await expect(workspace.getByText(t["common.saved"], { exact: true })).toBeVisible();
    await steps.screenshot({ path: info.outputPath("linked-plan.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-workspace"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.keyboard.press("Escape"); await expect(workspace).not.toBeVisible(); await open.click();
    await expect(link).toContainText(chosen);
    await workspace.getByRole("tab", { name: t["medical.tooth.title"], exact: true }).click();
    const chart = workspace.getByTestId("tooth-chart");
    const toothButton = chart.getByRole("button", { name: `${t["medical.tooth.tooth"]} 11: ${t["medical.tooth.empty"]}`, exact: true });
    let failToothRead = mobile;
    if (mobile) {
      await page.route("**/api/medical/encounters/tooth-plan/**", route => {
        if (failToothRead) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) });
        return route.continue();
      });
    }
    await toothButton.click();
    const inspector = page.getByTestId("tooth-inspector");
    const toothPlan = inspector.getByTestId("tooth-plan-steps");
    if (mobile) {
      await expect(toothPlan.getByRole("alert")).toBeVisible();
      failToothRead = false;
      await toothPlan.getByRole("button", { name: t["common.retry"], exact: true }).click();
    }
    await expect(toothPlan).toContainText(`Synthetic linked plan ${id}`);
    await expect(toothPlan).toContainText(chosen);
    await inspector.screenshot({ path: info.outputPath("tooth-linked-plan.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="tooth-inspector"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.keyboard.press("Escape");
    await expect(toothButton).toBeFocused();
    await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
    page.once("dialog", dialog => dialog.dismiss());
    await link.getByRole("button", { name: t["medical.plan.unlinkVisit"], exact: true }).click();
    await expect(link).toContainText(chosen);
    page.once("dialog", dialog => dialog.accept());
    await link.getByRole("button", { name: t["medical.plan.unlinkVisit"], exact: true }).click();
    await expect(link).not.toContainText(chosen);
    await save.click();
    await expect(workspace.getByText(t["common.saved"], { exact: true })).toBeVisible();
    await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
    await workspace.getByTestId("clinical-history").locator("button[aria-pressed]").first().click();
    const reader = workspace.getByTestId("clinical-version");
    await expect(reader).not.toContainText(chosen);
    await workspace.getByTestId("clinical-revisions").getByRole("button").filter({ hasText: new RegExp(`^${t["medical.clinical.revision"]} 2`) }).click();
    await expect(reader).toContainText(chosen);
    await reader.getByTestId("clinical-plan-history").screenshot({ path: info.outputPath("linked-plan-history.png") });
    expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain(`Synthetic linked plan ${id}`);
    if (language === "en" && mobile) {
      await workspace.getByRole("tab", { name: t["medical.clinical.note"], exact: true }).click();
      await page.route("**/api/medical/encounters/visit-steps/**", route => route.fulfill({
        status: 403, contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }),
      }));
      await link.getByRole("button", { name: t["medical.plan.linkVisit"], exact: true }).click();
      await expect(workspace.getByRole("alert")).toBeVisible();
      await expect(workspace.getByRole("textbox")).toHaveCount(0);
      await workspace.screenshot({ path: info.outputPath("link-access-denied.png") });
    }
  });
}
