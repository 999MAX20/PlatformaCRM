import { test, expect } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { execFileSync } from "node:child_process";
import AxeBuilder from "@axe-core/playwright";

requireIsolatedEnvironment();
const dictionaries = { ru, kk, en };
for (const language of ["ru", "kk", "en"] as const) {
  for (const viewport of ["desktop", "mobile"] as const) {
    test(`representatives ${language} ${viewport}: verify, read and revoke through real API`, async ({ page }, info) => {
      const t = dictionaries[language];
      await page.setViewportSize(viewport === "desktop" ? { width: 1440, height: 1000 } : { width: 390, height: 844 });
      await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("patient-reception@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
      await page.locator('form button[type="submit"]').click();
      const token = (await (await login).json()).access;
      await expect(page).toHaveURL(/\/app\//);
      const headers = { Authorization: `Bearer ${token}` };
      const result = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/?q=Representative%20fixture%20${language}%20${viewport}`, { headers });
      const body = await result.json();
      const client = body.results.find((item: { full_name: string }) => item.full_name === `Representative fixture ${language} ${viewport}`);
      const created = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/patients/`, {
        headers: { ...headers, "Idempotency-Key": `rep-patient-${language}-${viewport}` },
        data: { business_id: 1, branch_id: 1, client_id: client.id, demographics: {}, iin: null },
      });
      expect(created.status()).toBe(201);
      await page.goto(`/app/clients/${client.id}`);
      const panel = page.getByTestId("patient-representatives");
      const checkRecovery = language === "ru" && viewport === "desktop";
      const opener = panel.getByRole("button", { name: t["medical.repAdd"], exact: true });
      if (checkRecovery) {
        await opener.focus();
        await page.keyboard.press("Enter");
        await expect(page.getByRole("dialog")).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(page.getByRole("dialog")).toHaveCount(0);
        await expect(opener).toBeFocused();
      }
      await opener.click();
      let dialog = page.getByRole("dialog");
      await dialog.getByRole("button", { name: new RegExp(`^${t["medical.representative"]} `) }).click();
      await page.getByRole("option", { name: /Synthetic relative/ }).click();
      const basis = language === "ru" ? "Учебное основание" : language === "kk" ? "Оқу негіздемесі" : "Synthetic basis";
      const permission = language === "ru" ? "Получение документов" : language === "kk" ? "Құжаттарды алу" : "Receive documents";
      await dialog.getByRole("textbox", { name: basis, exact: true }).fill("Synthetic representative proof");
      await expect(dialog.getByRole("button", { name: t["medical.repVerify"], exact: true })).toBeDisabled();
      await dialog.getByRole("checkbox", { name: permission, exact: true }).check();
      const tomorrow = new Date(Date.now() + 86400000);
      const end = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      await dialog.getByLabel(t["medical.repUntil"], { exact: true }).fill(end);
      await expect(dialog.getByRole("button", { name: t["medical.repVerify"], exact: true })).toBeEnabled();
      await dialog.screenshot({ path: info.outputPath("representative-form.png") });
      const keys: string[] = [];
      if (checkRecovery) {
        expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
        await page.route("**/api/medical/patients/*/representatives/", async route => {
          if (route.request().method() !== "POST") return route.continue();
          keys.push(route.request().headers()["idempotency-key"]);
          if (keys.length === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) });
          return route.continue();
        });
        const failed = page.waitForResponse(r => r.url().endsWith("/representatives/") && r.request().method() === "POST");
        await dialog.getByRole("button", { name: t["medical.repVerify"], exact: true }).click();
        expect((await failed).status()).toBe(503);
        await expect(dialog.getByRole("textbox", { name: basis, exact: true })).toHaveValue("Synthetic representative proof");
        await expect(dialog.getByRole("checkbox", { name: permission, exact: true })).toBeChecked();
        await expect(dialog.getByLabel(t["medical.repUntil"], { exact: true })).toHaveValue(end);
        await dialog.screenshot({ path: info.outputPath("representative-retry.png") });
      }
      const verified = page.waitForResponse(r => r.url().endsWith("/representatives/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["medical.repVerify"], exact: true }).click();
      expect((await verified).status()).toBe(201);
      if (checkRecovery) {
        expect(keys).toHaveLength(2);
        expect(keys[0]).toBeTruthy();
        expect(keys[1]).toBe(keys[0]);
      }
      await expect(panel.getByText(permission, { exact: true })).toBeVisible();
      await expect(panel.getByText(t["medical.repStatus.active"], { exact: true })).toBeVisible();
      await panel.screenshot({ path: info.outputPath("representative-active.png") });
      await panel.getByRole("button", { name: t["medical.repRevoke"], exact: true }).click();
      dialog = page.getByRole("dialog");
      await dialog.getByRole("textbox", { name: t["medical.repReason"], exact: true }).fill("Synthetic revocation proof");
      await dialog.screenshot({ path: info.outputPath("representative-revoke.png") });
      if (checkRecovery) {
        const patient = await created.json();
        const listed = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/medical/patients/${patient.id}/representatives/?business_id=1&branch_id=1`, { headers });
        expect(listed.status()).toBe(200);
        const relation = (await listed.json()).results[0];
        const competing = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/patients/${patient.id}/representatives/${relation.id}/revoke/`, {
          headers: { ...headers, "Idempotency-Key": "representative-competing-revocation" },
          data: { business_id: 1, branch_id: 1, representative_client_id: relation.representative_client_id, expected_revision: relation.revision, reason: "Synthetic competing revocation" },
        });
        expect(competing.status()).toBe(200);
      }
      const revoked = page.waitForResponse(r => /\/representatives\/\d+\/revoke\/$/.test(r.url()) && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["medical.repRevoke"], exact: true }).click();
      expect((await revoked).status()).toBe(checkRecovery ? 409 : 200);
      if (checkRecovery) {
        await expect(dialog.getByRole("textbox", { name: t["medical.repReason"], exact: true })).toHaveValue("Synthetic revocation proof");
        await expect(dialog.getByRole("button", { name: t["medical.repRevoke"], exact: true })).toBeDisabled();
        await dialog.screenshot({ path: info.outputPath("representative-conflict.png") });
        await dialog.getByRole("button", { name: t["common.cancel"], exact: true }).click();
      }
      await expect(panel.getByText(t["medical.repStatus.revoked"], { exact: true })).toBeVisible();
      await expect(panel.getByRole("button", { name: t["medical.repRevoke"], exact: true })).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic representative proof");
    });
  }
}
for (const language of ["ru", "kk", "en"] as const) {
  for (const viewport of ["desktop", "mobile"] as const) {
    test(`${language} ${viewport}: real patient administrative lifecycle`, async ({ page }, info) => {
      const t = dictionaries[language];
      await page.setViewportSize(viewport === "desktop" ? { width: 1440, height: 1000 } : { width: 390, height: 844 });
      await page.addInitScript(locale => localStorage.setItem("ai_smb_language", locale), language);
      await page.goto("/login");
      await page.locator('input[name="email"]').fill("patient-reception@example.test");
      await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
      const loginResponse = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
      await page.locator('form button[type="submit"]').click();
      const response = await loginResponse;
      expect(response.status()).toBe(200);
      const token = (await response.json()).access;
      await expect(page).toHaveURL(/\/app\//);
      const clientsResponse = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/?q=Synthetic%20${language}%20${viewport}`, { headers: { Authorization: `Bearer ${token}` } });
      expect(clientsResponse.status()).toBe(200);
      const clients = await clientsResponse.json();
      const client = (clients.results ?? clients).find((item: { full_name: string }) => item.full_name === `Synthetic ${language} ${viewport}`);
      expect(client).toBeTruthy();
      await page.goto(`/app/clients/${client.id}`);
      const panel = page.getByTestId("patient-administration");
      await expect(panel.getByRole("button", { name: t["medical.create"], exact: true })).toBeVisible();
      await panel.getByRole("button", { name: t["medical.create"], exact: true }).click();
      let dialog = page.getByRole("dialog");
      await dialog.getByRole("textbox", { name: t["medical.address"], exact: true }).fill(`Synthetic address ${language} ${viewport}`);
      await dialog.getByRole("textbox", { name: t["medical.sex"], exact: true }).fill("Synthetic unspecified");
      await dialog.screenshot({ path: info.outputPath("create.png") });
      const created = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
      expect((await created).status()).toBe(201);
      await expect(panel.getByText(t["medical.unverified"], { exact: true })).toBeVisible();
      await panel.getByRole("button", { name: t["medical.edit"], exact: true }).click();
      dialog = page.getByRole("dialog");
      await dialog.getByRole("textbox", { name: t["medical.address"], exact: true }).fill("Corrected synthetic address");
      await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic preliminary correction");
      const updated = page.waitForResponse(r => r.url().endsWith("/preliminary/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
      expect((await updated).status()).toBe(200);
      await expect(panel.getByText("Corrected synthetic address", { exact: true })).toBeVisible();
      await panel.getByRole("button", { name: t["medical.verify"], exact: true }).click();
      dialog = page.getByRole("dialog");
      const basis = { ru: "Учебное основание", kk: "Оқу негіздемесі", en: "Synthetic basis" }[language];
      await dialog.getByRole("textbox", { name: basis, exact: true }).fill("Synthetic verification evidence");
      await dialog.screenshot({ path: info.outputPath("verify.png") });
      const verified = page.waitForResponse(r => r.url().endsWith("/verify/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["medical.verify"], exact: true }).click();
      expect((await verified).status()).toBe(200);
      await expect(panel.getByText(t["medical.verified"], { exact: true })).toBeVisible();
      await panel.getByRole("button", { name: t["medical.correct"], exact: true }).click();
      dialog = page.getByRole("dialog");
      const correctedName = `Corrected synthetic ${language} ${viewport}`;
      await dialog.getByRole("textbox", { name: t["medical.fullName"], exact: true }).fill(correctedName);
      await dialog.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Synthetic verified correction");
      await dialog.getByRole("textbox", { name: basis, exact: true }).fill("Synthetic repeated check");
      const corrected = page.waitForResponse(r => r.url().endsWith("/correct/") && r.request().method() === "POST");
      await dialog.getByRole("button", { name: t["common.save"], exact: true }).click();
      expect((await corrected).status()).toBe(200);
      await expect(panel.getByText(correctedName, { exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: correctedName, exact: true })).toBeVisible();
      await panel.screenshot({ path: info.outputPath("profile.png") });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Synthetic verification evidence");
    });
  }
}

test("recovery: keyboard, retained draft, idempotency, stale revision and real role revocation", async ({ page }, info) => {
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("patient-reception@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/clients/1");
  const panel = page.getByTestId("patient-administration");
  const opener = panel.getByRole("button", { name: ru["medical.create"], exact: true });
  await expect(opener).toBeVisible();
  await opener.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(opener).toBeFocused();
  await page.keyboard.press("Enter");
  let dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: ru["medical.address"], exact: true }).fill("Retained synthetic address");
  const keys: string[] = [];
  await page.route("**/api/medical/patients/", async route => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (keys.length === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) });
    await route.continue();
  });
  const first = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  expect((await first).status()).toBe(503);
  await expect(dialog.getByRole("textbox", { name: ru["medical.address"], exact: true })).toHaveValue("Retained synthetic address");
  await dialog.screenshot({ path: info.outputPath("retry.png") });
  const retry = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  const created = await retry;
  expect(created.status()).toBe(201);
  const patient = await created.json();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);
  await panel.getByRole("button", { name: ru["medical.edit"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: ru["medical.address"], exact: true }).fill("My stale draft");
  await dialog.getByRole("textbox", { name: ru["medical.reason"], exact: true }).fill("Synthetic reason");
  const competing = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/patients/${patient.id}/preliminary/`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": "competing-synthetic-command" },
    data: { business_id: 1, branch_id: 1, expected_revision: 1, demographics: { address: "Concurrent synthetic update" }, iin: null, reason: "Synthetic competing correction" },
  });
  expect(competing.status()).toBe(200);
  const stale = page.waitForResponse(r => r.url().endsWith("/preliminary/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  expect((await stale).status()).toBe(409);
  await expect(dialog.getByRole("textbox", { name: ru["medical.address"], exact: true })).toHaveValue("My stale draft");
  await expect(dialog.getByRole("button", { name: ru["common.save"], exact: true })).toBeDisabled();
  await dialog.screenshot({ path: info.outputPath("conflict.png") });
  await dialog.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(panel.getByText("Concurrent synthetic update", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: ru["medical.edit"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: ru["medical.reason"], exact: true }).fill("Must be denied");
  execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
  const revoked = page.waitForResponse(r => r.url().endsWith("/preliminary/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  expect((await revoked).status()).toBe(403);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(panel).not.toContainText("Concurrent synthetic update");
  await expect(panel).toContainText(ru["medical.denied"]);
  await panel.screenshot({ path: info.outputPath("denied.png") });
});

test("boundaries: branch switch, stale response, missing protocol, long values and accessibility", async ({ page }, info) => {
  execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "setup-boundaries"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("patient-reception@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/clients/2");
  const panel = page.getByTestId("patient-administration");
  await panel.getByRole("combobox").click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  await panel.getByRole("button", { name: ru["medical.create"], exact: true }).click();
  let dialog = page.getByRole("dialog");
  const longAddress = "Synthetic long address ".repeat(80);
  await dialog.getByRole("textbox", { name: ru["medical.address"], exact: true }).fill(longAddress);
  expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
  await dialog.screenshot({ path: info.outputPath("tablet-long-form.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await dialog.screenshot({ path: info.outputPath("mobile-long-form.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const created = page.waitForResponse(r => r.url().endsWith("/api/medical/patients/") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  const createdResponse = await created;
  expect(createdResponse.status()).toBe(201);
  const patient = await createdResponse.json();
  await expect(panel.getByText(ru["medical.unverified"], { exact: true })).toBeVisible();
  let captured!: () => void;
  let release!: () => void;
  const capturedRead = new Promise<void>(resolve => { captured = resolve; });
  const releaseRead = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/medical/patients/by-client/2/**", async route => {
    if (!route.request().url().includes("branch_id=2")) return route.continue();
    const old = await route.fetch();
    captured();
    await releaseRead;
    await route.fulfill({ response: old }).catch(() => {});
  });
  await panel.getByRole("combobox").click();
  await page.getByRole("option", { name: "Second synthetic branch", exact: true }).click();
  await capturedRead;
  await expect(panel).not.toContainText(longAddress.trim());
  const update = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/patients/${patient.id}/preliminary/`, {
    headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": "boundary-new-revision" },
    data: { business_id: 1, branch_id: 1, expected_revision: 1, demographics: { address: "Fresh branch context" }, iin: null, reason: "Synthetic newer state" },
  });
  expect(update.status()).toBe(200);
  await panel.getByRole("combobox").click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  await expect(panel.getByText("Fresh branch context", { exact: true })).toBeVisible();
  release();
  await page.unroute("**/api/medical/patients/by-client/2/**");
  await expect(panel).not.toContainText(longAddress.trim());
  let unavailable = true;
  await page.route("**/api/medical/patients/verification-form/**", async route => {
    if (!unavailable) return route.continue();
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "identity_verification_unavailable" }) });
  });
  await panel.getByRole("button", { name: ru["medical.verify"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: ru["medical.verify"], exact: true })).toBeDisabled();
  await expect(dialog.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  unavailable = false;
  await dialog.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(dialog.getByRole("textbox", { name: "Учебное основание", exact: true })).toBeVisible();
  expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
  await dialog.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(panel.getByText("Fresh branch context", { exact: true })).toBeVisible();
  await panel.screenshot({ path: info.outputPath("mobile-long-profile.png") });
});

test("representative boundaries mobile: protocol recovery, invalid authority and real role revocation", async ({ page }, info) => {
  execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "setup-boundaries"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("patient-reception@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await expect(page).toHaveURL(/\/app\//);
  const headers = { Authorization: `Bearer ${token}` };
  const clients = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/clients/?q=Representative%20boundary%20patient`, { headers });
  expect(clients.status()).toBe(200);
  const client = (await clients.json()).results[0];
  const created = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/medical/patients/`, {
    headers: { ...headers, "Idempotency-Key": "representative-boundary-patient" },
    data: { business_id: 1, branch_id: 1, client_id: client.id, demographics: {}, iin: null },
  });
  expect(created.status()).toBe(201);
  await page.goto(`/app/clients/${client.id}`);
  const medical = page.getByTestId("patient-administration");
  await medical.getByRole("combobox").click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  const panel = page.getByTestId("patient-representatives");
  let unavailable = true;
  await page.route("**/api/medical/patients/representative-form/**", route => unavailable
    ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }) : route.continue());
  await panel.getByRole("button", { name: ru["medical.repAdd"], exact: true }).click();
  const dialog = page.getByRole("dialog");
  const save = dialog.getByRole("button", { name: ru["medical.repVerify"], exact: true });
  await expect(save).toBeDisabled();
  await expect(dialog.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  await dialog.screenshot({ path: info.outputPath("mobile-protocol-unavailable.png") });
  unavailable = false;
  await dialog.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  await expect(dialog.getByRole("textbox", { name: "Учебное основание", exact: true })).toBeVisible();
  const picker = dialog.getByRole("button", { name: new RegExp(`^${ru["medical.representative"]} `) });
  await picker.click();
  await page.getByRole("option", { name: "Representative boundary patient", exact: true }).click();
  await expect(dialog.getByText(ru["medical.repSelectOther"], { exact: true })).toBeVisible();
  await expect(save).toBeDisabled();
  await picker.click();
  await page.getByRole("option", { name: /Synthetic long name/ }).click();
  await dialog.getByRole("textbox", { name: "Учебное основание", exact: true }).fill("Mobile retained authority proof");
  await dialog.getByRole("checkbox", { name: "Получение документов", exact: true }).check();
  const localDate = (offset: number) => {
    const date = new Date(Date.now() + offset);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  };
  await dialog.getByLabel(ru["medical.repUntil"], { exact: true }).fill(localDate(-86400000));
  const invalid = page.waitForResponse(r => r.url().endsWith("/representatives/") && r.request().method() === "POST");
  await save.click();
  expect((await invalid).status()).toBe(400);
  await expect(dialog.getByRole("textbox", { name: "Учебное основание", exact: true })).toHaveValue("Mobile retained authority proof");
  await expect(save).toBeEnabled();
  await dialog.getByLabel(ru["medical.repUntil"], { exact: true }).fill(localDate(86400000));
  expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
  await dialog.screenshot({ path: info.outputPath("mobile-retained-draft.png") });
  execFileSync(process.env.E2E_PYTHON!, ["e2e/medical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
  const denied = page.waitForResponse(r => r.url().endsWith("/representatives/") && r.request().method() === "POST");
  await save.click();
  expect((await denied).status()).toBe(403);
  await expect(dialog).toHaveCount(0);
  await expect(panel).toHaveCount(0);
  await expect(medical).toContainText(ru["medical.denied"]);
  await expect(medical).not.toContainText("Representative boundary patient");
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Mobile retained authority proof");
  await medical.screenshot({ path: info.outputPath("mobile-role-denied.png") });
});
