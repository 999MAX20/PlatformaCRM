import { execFileSync } from "node:child_process";
import { test, expect } from "@playwright/test";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";

requireIsolatedEnvironment();
for (const language of ["ru", "kk"] as const) test(`client clinical page ${language}: save and protect draft`, async ({ page }, info) => {
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/entity-pages-fixture.py"], { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  const t = { ru, kk }[language];
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.setViewportSize({ width: language === "ru" ? 1536 : 390, height: 1024 });
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(fixture.email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients/${fixture.client_id}`);
  const screen = page.getByTestId("client-reference-page");
  await expect(screen).toBeVisible();
  await page.screenshot({ path: info.outputPath(`client-overview-${language}.png`), fullPage: true });
  await screen.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
  const workspace = screen.getByTestId("clinical-workspace");
  await expect(workspace).toBeVisible();
  const complaint = workspace.getByLabel(t["medical.clinical.complaints"], { exact: true });
  await complaint.fill(`Independent page draft ${fixture.client_id}`);
  await screen.locator("#client-page-tab-overview").click();
  const guard = page.getByTestId("clinical-unsaved");
  await expect(guard).toBeVisible();
  await guard.getByRole("button", { name: t["medical.clinical.continueEditing"], exact: true }).click();
  await expect(complaint).toHaveValue(`Independent page draft ${fixture.client_id}`);
  await workspace.getByRole("button", { name: t["medical.clinical.save"], exact: true }).click();
  await expect(workspace.getByRole("status").filter({ hasText: t["common.saved"] })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`client-clinical-${language}.png`), fullPage: true });
  await screen.locator("#client-page-tab-overview").click();
  await expect(workspace).toHaveCount(0);
});

test("client edit recovery, list return and denied medical context", async ({ page }, info) => {
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/entity-pages-fixture.py"], { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.setViewportSize({ width: 1536, height: 1024 });
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(fixture.owner_email);
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/clients?page=2&page_size=20");
  await page.getByRole("row").filter({ hasText: "Анна Тестова" }).click();
  await expect(page).toHaveURL(new RegExp(`/app/clients/${fixture.client_id}`));
  const screen = page.getByTestId("client-reference-page");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByTestId("client-edit-action").click();
  const form = page.getByRole("dialog");
  const notes = form.locator('textarea[name="notes"]');
  await notes.fill(`Сохранённая заметка ${fixture.client_id}`);
  let fail = true;
  await page.route(`**/api/clients/${fixture.client_id}/`, route => {
    if (route.request().method() === "PATCH" && fail) { fail = false; return route.fulfill({ status: 503, json: { detail: "Synthetic temporary failure" } }); }
    return route.continue();
  });
  await form.getByTestId("client-action-submit").click();
  await expect(notes).toHaveValue(`Сохранённая заметка ${fixture.client_id}`);
  await form.getByTestId("client-action-submit").click();
  await expect(form).toHaveCount(0);
  await expect(screen.getByText(`Сохранённая заметка ${fixture.client_id}`, { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("client-owner-desktop.png"), fullPage: true });
  await screen.getByRole("tab", { name: "Медицинская карта", exact: true }).click();
  await expect(screen.getByTestId("clinical-workspace")).toHaveCount(0);
  await screen.getByRole("tab", { name: "Обзор", exact: true }).click();
  await screen.getByRole("link", { name: "Назад", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/clients\?/);
  expect(new URL(page.url()).searchParams.get("page")).toBe("2");
  await expect(page.getByRole("row").filter({ hasText: "Анна Тестова" })).toBeVisible();
});

test("client standalone desktop and mobile", async ({ page }, info) => {
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-new-appointment"], { env: process.env, windowsHide: true, encoding: "utf8" });
  const id = JSON.parse(output.trim().split(/\r?\n/).at(-1)!).appointment_id;
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${id}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const appointment = await response.json();
  await page.goto(`/app/clients/${appointment.client}`);
  const screen = page.getByTestId("client-reference-page");
  await expect(screen).toBeVisible();
  for (const width of [1536, 390]) {
    await page.setViewportSize({ width, height: 1024 });
    await expect(screen.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`client-${width}.png`), fullPage: true });
  }
  await screen.getByRole("tab", { name: "Записи", exact: true }).click();
  await expect(screen.locator(`[href="/app/appointments/${id}"]`)).toBeVisible();
  await screen.getByRole("tab", { name: "Обзор", exact: true }).click();
  await expect(screen.getByRole("heading", { name: "Контакты", exact: true })).toBeVisible();
});
