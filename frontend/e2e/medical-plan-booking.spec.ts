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
  test(`clinical booking ${language} ${mobile ? "mobile" : "desktop"}: confirmed calendar conversion`, async ({ page }, info) => {
    test.setTimeout(90_000);
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
    const businessId = (await (await page.request.get(`${api}/api/appointments/${id}/`, { headers })).json()).business;
    const context = await (await page.request.get(`${api}/api/medical/encounters/appointment-context/?business_id=${businessId}&appointment_id=${id}`, { headers })).json();
    const scope = { business_id: businessId, patient_id: context.patient.id };
    const record = await page.request.post(`${api}/api/medical/records/`, { headers: { ...headers, "Idempotency-Key": `booking-record-${id}` },
      data: { ...scope, appointment_id: id, expected_patient_revision: context.patient.revision, number: `BOOK-${id}` } });
    expect(record.status()).toBe(201);
    const encounter = await page.request.post(`${api}/api/medical/encounters/`, { headers: { ...headers, "Idempotency-Key": `booking-open-${id}` },
      data: { ...scope, appointment_id: id, record_id: (await record.json()).id,
        expected_patient_revision: context.patient.revision, expected_appointment_updated_at: context.appointment.updated_at,
        content: { plan_steps: [{ id: `00000000-0000-4000-8000-${String(id).padStart(12, "0")}`, description: `Private synthetic booking plan ${id}` }] } } });
    expect(encounter.status()).toBe(201);
    const encounterId = (await encounter.json()).id;
    await page.goto(`/app/calendar?appointment=${id}&date=${context.appointment.start_at.slice(0, 10)}`);
    await page.getByTestId("clinical-appointment-entry").getByRole("button", { name: t["medical.clinical.open"], exact: true }).click();
    const workspace = page.getByTestId("clinical-workspace");
    const openBooking = workspace.getByRole("button", { name: t["medical.plan.book"], exact: true });
    await openBooking.click();
    const dialog = page.getByTestId("clinical-plan-booking");
    const client = dialog.getByRole("textbox", { name: t["appointment.client"], exact: true });
    await expect(client).toHaveValue(context.patient.full_name);
    await expect(client).toHaveAttribute("readonly", "");
    await dialog.getByRole("combobox", { name: new RegExp(`^${t["appointment.resource"]}`) }).click();
    await page.getByRole("option", { name: "Specialist", exact: true }).click();
    const future = new Date(); future.setUTCDate(future.getUTCDate() + 3);
    await dialog.getByLabel(t["appointment.date"], { exact: true }).fill(future.toISOString().slice(0, 10));
    await expect(dialog.getByTestId("appointment-submit")).toBeEnabled();
    await dialog.getByRole("combobox", { name: new RegExp(`^${t["appointment.slot"]}`) }).click();
    await page.getByRole("option").filter({ hasText: /^\d{1,2}:\d{2}/ }).first().click();
    const notes = dialog.getByRole("textbox", { name: t["appointment.notes"], exact: true });
    await expect(notes).toHaveValue("");
    await notes.fill("Synthetic administrative booking note");
    page.once("dialog", prompt => prompt.dismiss());
    await page.keyboard.press("Escape");
    await expect(notes).toHaveValue("Synthetic administrative booking note");
    await dialog.screenshot({ path: info.outputPath("booking-form.png") });
    expect((await new AxeBuilder({ page }).include('[data-testid="clinical-plan-booking"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    const keys: string[] = [];
    let loseResponse = language === "ru" && !mobile;
    await page.route(`**/api/medical/encounters/${encounterId}/book-plan-step/`, async route => {
      keys.push(route.request().headers()["idempotency-key"]);
      const response = await route.fetch();
      if (loseResponse) { loseResponse = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
      return route.fulfill({ response });
    });
    if (mobile) {
      page.once("dialog", prompt => prompt.dismiss());
      await dialog.getByTestId("appointment-submit").click();
      expect(keys).toHaveLength(0);
    }
    page.once("dialog", prompt => prompt.accept());
    await dialog.getByTestId("appointment-submit").click();
    if (language === "ru" && !mobile) {
      await expect(dialog.getByRole("alert")).toBeVisible();
      await expect(notes).toHaveValue("Synthetic administrative booking note");
      page.once("dialog", prompt => prompt.accept());
      await dialog.getByTestId("appointment-submit").click();
    }
    await expect(dialog.getByRole("status")).toHaveText(t["medical.plan.booked"]);
    if (language === "ru" && !mobile) { expect(keys).toHaveLength(2); expect(keys[1]).toBe(keys[0]); }
    else expect(keys).toHaveLength(1);
    await dialog.screenshot({ path: info.outputPath("booking-result.png") });
    await dialog.getByRole("button", { name: t["common.close"], exact: true }).last().click();
    await expect(dialog).not.toBeVisible();
    await expect(workspace.getByTestId("clinical-visit-link")).toContainText("Synthetic service");
    await workspace.getByTestId("clinical-plan-steps").screenshot({ path: info.outputPath("booked-clinical-plan.png") });
    await openBooking.click();
    await expect(dialog.getByRole("alert")).toHaveText(t["medical.plan.reviewBooking"]);
    await expect(dialog.getByTestId("appointment-form")).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(openBooking).toBeFocused();
    if (language === "en" && mobile) {
      await page.route(/\/api\/visit-plans\/\d+\//, route => route.fulfill({ status: 403,
        contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
      await openBooking.click();
      await expect(workspace.getByRole("alert")).toBeVisible();
      await expect(workspace.getByRole("textbox")).toHaveCount(0);
      await workspace.screenshot({ path: info.outputPath("booking-denied.png") });
    }
    if (language === "ru" && !mobile) {
      await page.goto(`/app/calendar?date=${future.toISOString().slice(0, 10)}&branch=${context.appointment.branch_id}`);
      await page.getByRole("button", { name: t["calendar.newBooking"], exact: true }).first().click();
      const ordinary = page.getByTestId("appointment-form");
      await ordinary.getByRole("button", { name: new RegExp(`^${t["appointment.client"]} `) }).click();
      await page.getByPlaceholder(t["common.search"], { exact: true }).fill(context.patient.full_name);
      await page.getByRole("option", { name: context.patient.full_name, exact: true }).click();
      await ordinary.getByRole("combobox", { name: new RegExp(`^${t["appointment.resource"]}`) }).click();
      await page.getByRole("option", { name: "Specialist", exact: true }).click();
      await expect(ordinary.getByTestId("appointment-submit")).toBeEnabled();
      await ordinary.getByRole("combobox", { name: new RegExp(`^${t["appointment.slot"]}`) }).click();
      await page.getByRole("option").filter({ hasText: /^\d{1,2}:\d{2}/ }).first().click();
      await ordinary.screenshot({ path: info.outputPath("ordinary-booking.png") });
      await ordinary.getByTestId("appointment-submit").click();
      await expect(ordinary).not.toBeVisible();
    }
  });
}
