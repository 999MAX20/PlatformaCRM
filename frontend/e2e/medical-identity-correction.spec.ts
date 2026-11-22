import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.skip(process.env.E2E_IDENTITY_CORRECTION !== "1", "Requires isolated identity correction fixtures");

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

test("identity correction recovery: stale review, rejection retry and access denial", async ({ page, browser }, info) => {
  const headers = await login(page, "patient-reception@example.test", "ru");
  const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers, params: { q: "Correction fixture ru 1440" } });
  const client = (await clients.json()).results.find((item: { full_name: string }) => item.full_name === "Correction fixture ru 1440");
  const root = `${process.env.E2E_API_BASE_URL}/api/medical/patients/`;
  const scope = { business_id: 1, branch_id: 1 };
  const patientResponse = await page.request.get(`${root}by-client/${client.id}/`, { headers, params: scope });
  expect(patientResponse.status()).toBe(200);
  const patient = await patientResponse.json();
  const verification = { ...scope, expected_revision: patient.revision, expected_client_updated_at: patient.client_updated_at,
    protocol_reference: "synthetic-browser-v1", method: "synthetic", fields: { basis: "Synthetic repeat proof" } };
  const requested = await page.request.post(`${root}${patient.id}/iin-correction/`, {
    headers: { ...headers, "Idempotency-Key": crypto.randomUUID() },
    data: { ...verification, iin: String(Date.now()).slice(-12), reason: "Synthetic stale correction" },
  });
  expect(requested.status()).toBe(201);
  const correctionId = (await requested.json()).id;
  const changed = await page.request.post(`${root}${patient.id}/correct/`, {
    headers: { ...headers, "Idempotency-Key": crypto.randomUUID() },
    data: { ...verification, full_name: patient.full_name, demographics: patient.demographics, reason: "Synthetic concurrent identity check" },
  });
  expect(changed.status()).toBe(200);
  const context = await browser.newContext({ baseURL: process.env.E2E_BASE_URL, viewport: { width: 390, height: 1000 } });
  try {
    const head = await context.newPage();
    await login(head, "identity-review-head@example.test", "ru");
    await head.goto(`/app/clients/${client.id}`);
    const row = head.getByTestId(`identity-correction-${correctionId}`);
    await row.getByRole("button", { name: ru["medical.correction.approve"], exact: true }).click();
    let dialog = head.getByRole("dialog");
    await dialog.getByRole("textbox", { name: ru["medical.correction.decisionReason"], exact: true }).fill("Synthetic stale decision");
    const stale = head.waitForResponse(r => r.url().endsWith("/decision/"));
    await dialog.getByRole("button", { name: ru["medical.correction.approve"], exact: true }).click();
    expect((await stale).status()).toBe(409);
    await expect(dialog.getByRole("textbox")).toHaveValue("Synthetic stale decision");
    await dialog.screenshot({ path: info.outputPath("stale-review.png") });
    head.once("dialog", message => message.accept());
    await dialog.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
    await expect(dialog).toHaveCount(0);
    const reject = row.getByRole("button", { name: ru["medical.correction.reject"], exact: true });
    await reject.click(); await head.keyboard.press("Escape"); await expect(reject).toBeFocused();
    await reject.click(); dialog = head.getByRole("dialog");
    await dialog.getByRole("textbox", { name: ru["medical.correction.decisionReason"], exact: true }).fill("Synthetic rejection after stale review");
    const keys: string[] = [];
    await head.route(`**/identity-corrections/${correctionId}/decision/`, async route => {
      keys.push(route.request().headers()["idempotency-key"]);
      return keys.length === 1 ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue();
    });
    const submit = dialog.getByRole("button", { name: ru["medical.correction.reject"], exact: true });
    await submit.click(); await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(dialog.getByRole("textbox")).toHaveValue("Synthetic rejection after stale review");
    await dialog.screenshot({ path: info.outputPath("rejection-retry.png") });
    await submit.click(); await expect(row.getByText(ru["medical.correction.rejected"], { exact: true })).toBeVisible();
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await head.route("**/api/medical/patients/identity-corrections/?**", route => route.fulfill({ status: 403,
      contentType: "application/json", body: JSON.stringify({ code: "permission_denied" }) }));
    await head.getByTestId("identity-corrections").getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
    const medical = head.getByTestId("patient-administration");
    await expect(medical).toContainText(ru["medical.denied"]);
    await expect(head.getByTestId("identity-corrections")).toHaveCount(0);
    await medical.screenshot({ path: info.outputPath("correction-access-denied.png") });
  } finally { await context.close(); }
});

for (const language of ["ru", "kk", "en"] as const) {
  for (const width of [1440, 390]) {
    test(`identity correction ${language} ${width}: reception request and head review`, async ({ page, browser }, info) => {
      const t = { ru, kk, en }[language];
      await page.setViewportSize({ width, height: 1000 });
      const headers = await login(page, "patient-reception@example.test", language);
      const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/`, { headers,
        params: { q: `Correction fixture ${language} ${width}` } });
      expect(clients.status()).toBe(200);
      const client = (await clients.json()).results.find((item: { full_name: string }) => item.full_name === `Correction fixture ${language} ${width}`);
      await page.goto(`/app/clients/${client.id}`);
      await page.getByRole("button", { name: t["medical.correctIin"], exact: true }).click();
      const dialog = page.getByRole("dialog");
      const iin = String(Date.now()).slice(-12);
      await dialog.getByRole("textbox", { name: t["medical.correction.proposedIin"], exact: true }).fill(iin);
      await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic correction reason");
      await dialog.getByRole("textbox", { name: language === "ru" ? "Учебное основание" : language === "kk" ? "Оқу негіздемесі" : "Synthetic basis", exact: true }).fill("Synthetic repeat check");
      if (language === "ru" && width === 1440) {
        page.once("dialog", message => message.dismiss());
        await page.keyboard.press("Escape"); await expect(dialog).toBeVisible();
        let fail = true;
        await page.route("**/api/medical/patients/*/iin-correction/", async route => {
          if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
          return route.continue();
        });
        await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
        await expect(dialog.getByRole("alert")).toBeVisible();
        await expect(dialog.getByRole("textbox", { name: t["medical.correction.proposedIin"], exact: true })).toHaveValue(iin);
      }
      await dialog.screenshot({ path: info.outputPath("iin-request.png") });
      const requested = page.waitForResponse(r => r.url().endsWith("/iin-correction/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
      const requestResponse = await requested;
      expect(requestResponse.status()).toBe(201);
      const correctionId = (await requestResponse.json()).id;
      const panel = page.getByTestId("identity-corrections");
      const row = panel.getByTestId(`identity-correction-${correctionId}`);
      await expect(row.getByText(t["medical.correction.pending"], { exact: true })).toBeVisible();
      await expect(panel.getByRole("button", { name: t["medical.correction.approve"], exact: true })).toHaveCount(0);
      const reviewer = await browser.newContext({ baseURL: process.env.E2E_BASE_URL, viewport: { width, height: 1000 } });
      try {
        const head = await reviewer.newPage();
        await login(head, "identity-review-head@example.test", language);
        await head.goto(`/app/clients/${client.id}`);
        const reviewPanel = head.getByTestId("identity-corrections");
        const reviewRow = reviewPanel.getByTestId(`identity-correction-${correctionId}`);
        const approve = reviewRow.getByRole("button", { name: t["medical.correction.approve"], exact: true });
        await approve.click();
        await head.keyboard.press("Escape"); await expect(head.getByRole("dialog")).toHaveCount(0); await expect(approve).toBeFocused();
        await approve.click();
        const review = head.getByRole("dialog");
        await review.getByRole("textbox", { name: t["medical.correction.decisionReason"], exact: true }).fill("Synthetic head review");
        if (language === "ru" && width === 1440) expect((await new AxeBuilder({ page: head }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
        await review.screenshot({ path: info.outputPath("iin-review.png") });
        const decided = head.waitForResponse(r => r.url().endsWith("/decision/") && r.request().method() === "POST");
        await review.getByRole("button", { name: t["medical.correction.approve"], exact: true }).click();
        expect((await decided).status()).toBe(200);
        await expect(reviewRow.getByText(t["medical.correction.applied"], { exact: true })).toBeVisible();
        expect(await head.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      } finally { await reviewer.close(); }
      await panel.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
      await expect(row.getByText(t["medical.correction.applied"], { exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    });
  }
}
