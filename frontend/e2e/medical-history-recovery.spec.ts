import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { ru } from "../src/lib/i18n/ru";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test("history recovery: unavailable list, retained draft and revoked read", async ({ page }, info) => {
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  const headers = { Authorization: `Bearer ${token}` };
  const api = process.env.E2E_API_BASE_URL!;
  const scope = { business_id: 1, patient_id: 8 };
  const contextResponse = await page.request.get(`${api}/api/medical/encounters/appointment-context/?business_id=1&appointment_id=8`, { headers });
  expect(contextResponse.status()).toBe(200);
  const context = await contextResponse.json();
  await page.goto(`/app/calendar?appointment=8&date=${context.appointment.start_at.slice(0, 10)}`);
  await page.getByTestId("clinical-appointment-entry").getByRole("button", { name: ru["medical.clinical.open"], exact: true }).click();
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByRole("tab", { name: ru["medical.clinical.history"], exact: true }).click();
  await expect(workspace.getByText(ru["medical.clinical.historyEmpty"], { exact: true })).toBeVisible();
  await workspace.screenshot({ path: info.outputPath("history-empty-mobile.png") });
  await page.keyboard.press("Escape");
  await expect(workspace).not.toBeVisible();
  const record = await page.request.post(`${api}/api/medical/records/`, { headers: { ...headers, "Idempotency-Key": "history-recovery-record" },
    data: { ...scope, appointment_id: 8, expected_patient_revision: 1, number: "HISTORY-RECOVERY" } });
  expect(record.status()).toBe(201);
  const encounter = await page.request.post(`${api}/api/medical/encounters/`, { headers: { ...headers, "Idempotency-Key": "history-recovery-open" },
    data: { ...scope, appointment_id: 8, record_id: (await record.json()).id, expected_patient_revision: 1,
      expected_appointment_updated_at: context.appointment.updated_at } });
  expect(encounter.status()).toBe(201);
  const encounterId = (await encounter.json()).id;
  for (let revision = 1; revision <= 20; revision++) {
    const saved = await page.request.post(`${api}/api/medical/encounters/${encounterId}/draft/`, {
      headers: { ...headers, "Idempotency-Key": `history-page-${revision}` },
      data: { ...scope, expected_revision: revision, content: { complaints: `Synthetic revision ${revision + 1}` } },
    });
    expect(saved.status()).toBe(200);
  }
  await page.goto(`/app/calendar?appointment=8&date=${context.appointment.start_at.slice(0, 10)}`);
  await page.getByTestId("clinical-appointment-entry").getByRole("button", { name: ru["medical.clinical.open"], exact: true }).click();
  const complaint = workspace.getByLabel(ru["medical.clinical.complaints"], { exact: true });
  await complaint.fill("Unsaved draft retained through history error");
  let unavailable = true;
  await page.route("**/api/medical/encounters/workspace/**", route => unavailable
    ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue());
  await workspace.getByRole("tab", { name: ru["medical.clinical.history"], exact: true }).click();
  await expect(workspace.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  await workspace.screenshot({ path: info.outputPath("history-unavailable-mobile.png") });
  unavailable = false;
  await workspace.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await workspace.getByTestId("clinical-history").locator("button[aria-pressed]").first().click();
  const reader = workspace.getByTestId("clinical-version");
  await expect(reader).toContainText("Synthetic revision 21");
  const revisions = workspace.getByTestId("clinical-revisions");
  await expect(revisions.locator("button[aria-pressed]")).toHaveCount(20);
  await revisions.getByRole("button", { name: ru["medical.clinical.older"], exact: true }).click();
  await expect(revisions.locator("button[aria-pressed]")).toHaveCount(1);
  await expect(reader).toContainText(ru["medical.clinical.notRecorded"]);
  await expect(reader).not.toContainText("Synthetic revision 21");
  await workspace.screenshot({ path: info.outputPath("history-older-mobile.png") });
  let versionUnavailable = true;
  await page.route("**/api/medical/encounters/versions/**", route => versionUnavailable
    ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue());
  await revisions.getByRole("button", { name: ru["medical.clinical.newest"], exact: true }).click();
  await expect(revisions.locator("button[aria-pressed]")).toHaveCount(20);
  await expect(reader).toHaveCount(0);
  await expect(revisions.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  versionUnavailable = false;
  await revisions.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(reader).toContainText("Synthetic revision 21");
  await workspace.getByRole("tab", { name: ru["medical.clinical.note"], exact: true }).click();
  await expect(complaint).toHaveValue("Unsaved draft retained through history error");
  await workspace.getByRole("tab", { name: ru["medical.clinical.history"], exact: true }).click();
  await expect(workspace.getByTestId("clinical-history")).toBeVisible();
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
  const denied = page.waitForResponse(r => r.url().includes("/revisions/") && r.request().method() === "GET");
  await workspace.getByTestId("clinical-history").locator("button[aria-pressed]").first().click();
  expect((await denied).status()).toBe(403);
  await expect(workspace.getByText(ru["medical.denied"], { exact: true })).toBeVisible();
  await expect(workspace.locator("textarea")).toHaveCount(0);
  await expect(workspace.getByTestId("clinical-history")).toHaveCount(0);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Unsaved draft retained through history error");
  await workspace.screenshot({ path: info.outputPath("history-revoked-mobile.png") });
});
