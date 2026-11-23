import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { openClinicalWorkspace } from "./clinical-card-navigation";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

requireIsolatedEnvironment();
function newFileAppointment(): number {
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-new-appointment"], {
    env: process.env, windowsHide: true, encoding: "utf8",
  });
  return JSON.parse(output.trim().split(/\r?\n/).at(-1)!).appointment_id;
}

test("medical files correction entry: reason, recovery and return focus", async ({ page }, info) => {
  test.setTimeout(120000);
  const appointmentId = newFileAppointment();
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-access-prepare", String(appointmentId)],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  const t = ru;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients/${fixture.client_id}`);
  const administration = page.getByTestId("patient-administration");
  await administration.getByLabel(t["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  const entry = page.getByTestId(`correction-access-${fixture.correction_id}`).getByRole("button", { name: t["medical.files.title"], exact: true });
  await entry.click();
  const files = page.getByTestId("medical-files");
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Synthetic-correction.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\nSynthetic") });
  const submit = files.locator('button[type="submit"]');
  await expect(submit).toBeDisabled();
  const reason = files.getByRole("textbox", { name: t["medical.reason"], exact: true });
  await reason.fill("Synthetic missing attachment");
  const commands: string[] = [];
  let fail = true;
  await page.route(url => url.pathname === "/api/medical/files/", route => {
    if (route.request().method() !== "POST") return route.continue();
    commands.push(route.request().headers()["idempotency-key"]);
    if (fail) { fail = false; return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "service_unavailable" }) }); }
    return route.continue();
  });
  await submit.click();
  await expect(files.getByRole("alert")).toBeVisible();
  await expect(reason).toHaveValue("Synthetic missing attachment");
  await reason.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("correction-retained-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await reason.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("correction-retained-mobile.png") });
  await files.getByRole("alert").evaluate(element => element.scrollIntoView({ block: "center" }));
  await page.screenshot({ path: info.outputPath("correction-retry-mobile.png") });
  const saved = page.waitForResponse(r => r.url().endsWith("/api/medical/files/") && r.request().method() === "POST");
  await submit.click();
  expect((await saved).status()).toBe(201);
  expect(commands).toHaveLength(2); expect(commands[0]).toBe(commands[1]);
  await files.getByRole("button", { name: "Synthetic-correction.pdf", exact: true }).click();
  await files.getByRole("button", { name: t["medical.files.history"], exact: true }).click();
  await expect(files.getByText("Synthetic missing attachment", { exact: true })).toBeVisible();
  await administration.getByRole("button", { name: t["common.back"], exact: true }).click();
  await expect(entry).toBeFocused();
});

test("medical files participation and head entries without a current appointment", async ({ page, browser }, info) => {
  test.setTimeout(120000);
  const appointmentId = newFileAppointment();
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-access-prepare", String(appointmentId)],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  const t = ru;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/calendar");
  await page.locator("summary").filter({ hasText: t["medical.participation.title"] }).click();
  await page.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
  const row = page.getByTestId(`participation-row-${fixture.participation_id}`);
  await row.getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  const files = page.getByTestId("medical-files");
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  await files.getByRole("textbox", { name: t["medical.files.description"], exact: true }).fill("Synthetic participation file");
  await expect(files.getByRole("textbox", { name: t["medical.reason"], exact: true })).toHaveCount(0);
  const back = page.getByRole("dialog").getByRole("button", { name: t["common.back"], exact: true });
  page.once("dialog", dialog => dialog.dismiss()); await back.click();
  await expect(files.getByRole("textbox", { name: t["medical.files.description"], exact: true })).toHaveValue("Synthetic participation file");
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Synthetic-participation.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\nSynthetic") });
  const saved = page.waitForResponse(r => r.url().endsWith("/api/medical/files/") && r.request().method() === "POST");
  await files.locator('button[type="submit"]').click(); expect((await saved).status()).toBe(201);
  await expect(files.getByRole("button", { name: "Synthetic-participation.pdf", exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("participation-files-desktop.png") });
  await back.click(); await expect(row).toBeFocused();

  const headContext = await browser.newContext({ viewport: { width: 390, height: 844 }, baseURL: process.env.E2E_BASE_URL });
  try {
    const head = await headContext.newPage();
    await head.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await head.goto("/login");
    await head.locator('input[name="email"]').fill("medical-participation-head@example.test");
    await head.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
    await head.locator('form button[type="submit"]').click(); await expect(head).toHaveURL(/\/app\//);
    await head.goto(`/app/clients/${fixture.client_id}`);
    const profile = head.getByTestId("patient-administration");
    await profile.getByLabel(t["medical.branch"], { exact: true }).click();
    await head.getByRole("option", { name: "First", exact: true }).click();
    await profile.getByRole("button", { name: t["medical.participation.title"], exact: true }).click();
    await head.locator('[data-participation-focus="files"]').click();
    const headFiles = head.getByTestId("medical-files");
    await headFiles.getByRole("button", { name: "Synthetic-participation.pdf", exact: true }).click();
    await expect(headFiles.getByText("Synthetic participation file", { exact: true })).toBeVisible();
    await expect(headFiles.getByRole("button", { name: t["medical.edit"], exact: true })).toHaveCount(0);
    await head.screenshot({ path: info.outputPath("head-files-mobile.png") });
  } finally { await headContext.close(); }
});
test("direct patient card participation: inline files, draft guard and revoked access", async ({ page }, info) => {
  test.setTimeout(120000);
  const appointmentId = newFileAppointment();
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-access-prepare", String(appointmentId)],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  const t = ru;
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click(); await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients?client=${fixture.client_id}&tab=timeline`);
  const dialog = page.getByRole("dialog", { name: t["common.client"], exact: true });
  await dialog.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
  await dialog.getByLabel(t["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  const card = page.getByTestId("participation-card");
  await expect(card.getByTestId("clinical-overview")).toBeVisible();
  await expect(dialog.getByRole("combobox", { name: t["medical.clinical.title"], exact: true })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await card.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = card.getByTestId("medical-files");
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  const description = files.getByRole("textbox", { name: t["medical.files.description"], exact: true });
  await description.fill("Synthetic direct-card retained draft");
  page.once("dialog", prompt => prompt.dismiss());
  await card.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
  await expect(description).toHaveValue("Synthetic direct-card retained draft");
  page.once("dialog", prompt => prompt.dismiss()); await page.keyboard.press("Escape");
  await expect(description).toHaveValue("Synthetic direct-card retained draft");
  await page.screenshot({ path: info.outputPath("direct-participation-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await description.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("direct-participation-mobile.png") });
  page.once("dialog", prompt => prompt.accept());
  await card.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
  await card.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  await expect(description).toHaveValue("");
  await files.getByRole("button", { name: t["common.cancel"], exact: true }).click();
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-end-participation", String(fixture.participation_id)],
    { env: process.env, windowsHide: true, stdio: "pipe" });
  await files.getByRole("button", { name: t["common.refresh"], exact: true }).click();
  await expect(card).toHaveCount(0);
  await expect(dialog.getByText(t["medical.denied"], { exact: true })).toBeVisible();
});

for (const [language, t] of [["kk", kk], ["en", en]] as const) {
test(`direct participation FDI files localization ${language}`, async ({ page }, info) => {
  test.setTimeout(120000);
  const appointmentId = newFileAppointment();
  const output = execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-access-prepare", String(appointmentId)],
    { env: process.env, windowsHide: true, encoding: "utf8" });
  const fixture = JSON.parse(output.trim().split(/\r?\n/).at(-1)!);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click(); await expect(page).toHaveURL(/\/app\//);
  await page.goto(`/app/clients?client=${fixture.client_id}&tab=timeline`);
  const dialog = page.getByRole("dialog", { name: t["common.client"], exact: true });
  await dialog.getByRole("tab", { name: t["medical.clinical.title"], exact: true }).click();
  await dialog.getByLabel(t["medical.branch"], { exact: true }).click();
  await page.getByRole("option", { name: "First", exact: true }).click();
  const card = page.getByTestId("participation-card");
  await expect(card.getByTestId("clinical-overview")).toBeVisible();
  await card.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = card.getByTestId("medical-files");
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Synthetic-FDI-21.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=", "base64") });
  await files.getByLabel(t["medical.files.description"], { exact: true }).fill("Synthetic localized file flow");
  await files.getByTestId("clinical-plan-teeth").getByRole("combobox").click();
  await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 21`, exact: true }).click();
  await files.locator('button[type="submit"]').click();
  const file = files.getByRole("button", { name: "Synthetic-FDI-21.png", exact: true });
  await expect(file).toBeVisible();
  await card.getByRole("tab", { name: t["medical.tooth.title"], exact: true }).click();
  const chart = card.getByTestId("tooth-chart");
  const tooth21 = chart.getByRole("button", { name: `${t["medical.tooth.tooth"]} 21: ${t["medical.tooth.empty"]}`, exact: true });
  await tooth21.click();
  await page.getByTestId("tooth-inspector").getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  await expect(card.getByRole("tab", { name: t["medical.files.title"], exact: true })).toHaveAttribute("aria-selected", "true");
  const filter = files.getByRole("combobox", { name: new RegExp(`^${t["medical.tooth.tooth"]} `) });
  await expect(filter).toContainText("21");
  await expect(file).toBeEnabled();
  await expect(page.getByRole("dialog")).toHaveCount(1);
  await page.screenshot({ path: info.outputPath(`direct-fdi-${language}-desktop.png`) });
  await filter.click();
  await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 11`, exact: true }).click();
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await card.getByRole("tab", { name: t["medical.tooth.title"], exact: true }).click();
  await chart.getByRole("combobox", { name: new RegExp(`^${t["medical.tooth.orientation"]}`) }).click();
  await page.getByRole("option", { name: t["medical.tooth.q2"], exact: true }).click();
  await tooth21.click();
  await page.getByTestId("tooth-inspector").getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  await expect(filter).toContainText("21");
  await expect(file).toBeEnabled();
  await filter.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath(`direct-fdi-${language}-mobile.png`) });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await file.click();
  await expect(files.getByText("Synthetic localized file flow", { exact: true })).toBeVisible();
  await expect(files.getByRole("button", { name: t["medical.files.preview"], exact: true })).toBeDisabled();
  await files.getByRole("button", { name: t["medical.files.back"], exact: true }).click();
  await expect(file).toBeVisible();
});
}

test("medical files RU desktop: upload quarantine preview download and history", async ({ page }, info) => {
  test.setTimeout(90000);
  const t = ru;
  const appointmentId = newFileAppointment();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await me; await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${appointmentId}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const appointment = await response.json();
  await page.goto(`/app/calendar?appointment=${appointmentId}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`FILES-SYNTHETIC-${appointmentId}`);
  await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await workspace.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = workspace.getByTestId("medical-files");
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  const syntheticImage = await page.evaluate(() => {
    const canvas = document.createElement("canvas"); canvas.width = 480; canvas.height = 240;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#e6eef5"; context.fillRect(0, 0, 480, 240);
    context.fillStyle = "#224466"; context.fillRect(24, 24, 64, 64);
    context.font = "24px sans-serif"; context.fillText("SYNTHETIC IMAGE", 24, 150);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Synthetic-image.png", mimeType: "image/png",
    buffer: Buffer.from(syntheticImage, "base64") });
  await files.getByLabel(t["medical.files.description"], { exact: true }).fill("Synthetic image for file flow verification");
  await files.locator('button[type="submit"]').click();
  await expect(files.getByRole("button", { name: "Synthetic-image.png", exact: true })).toBeVisible();
  await files.getByRole("button", { name: "Synthetic-image.png", exact: true }).click();
  await expect(files.getByRole("button", { name: t["medical.files.preview"], exact: true })).toBeDisabled();
  await expect(files.getByText(t["medical.files.pending"], { exact: false })).toBeVisible();
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-scan"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await files.getByRole("button", { name: t["common.refresh"], exact: true }).click();
  await expect(files.getByText(t["medical.files.clean"], { exact: false })).toBeVisible();
  await page.route(/\/api\/medical\/files\/\d+\/preview\//, route => route.fulfill({
    status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic preview outage" }),
  }), { times: 1 });
  await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
  await expect(files.getByRole("alert")).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
  const image = files.getByRole("img", { name: "Synthetic-image.png", exact: true });
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0);
  await page.screenshot({ path: info.outputPath("files-desktop.png"), fullPage: true });
  const download = page.waitForEvent("download");
  await files.getByRole("button", { name: t["medical.files.download"], exact: true }).click();
  expect((await download).suggestedFilename()).toBe("Synthetic-image.png");
  await expect(image).toBeVisible();
  await files.getByRole("button", { name: t["medical.edit"], exact: true }).click();
  const metadata = files.getByTestId("medical-file-metadata");
  await expect(metadata.getByRole("textbox", { name: t["medical.files.description"], exact: true })).toBeFocused();
  await metadata.getByRole("textbox", { name: t["medical.files.description"], exact: true }).fill("Updated synthetic description");
  await metadata.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Corrected synthetic tooth link");
  await metadata.getByTestId("clinical-plan-teeth").getByRole("combobox").click();
  await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 21`, exact: true }).click();
  await page.screenshot({ path: info.outputPath("file-metadata-desktop.png"), fullPage: true });
  const metadataKeys: (string | undefined)[] = [];
  page.on("request", request => {
    if (/\/api\/medical\/files\/\d+\/metadata\//.test(request.url()) && request.method() === "POST") metadataKeys.push(request.headers()["idempotency-key"]);
  });
  await page.route(/\/api\/medical\/files\/\d+\/metadata\//, route => route.fulfill({
    status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic metadata outage" }),
  }), { times: 1 });
  await metadata.getByRole("button", { name: t["common.save"], exact: true }).click();
  await expect(metadata.getByRole("alert")).toBeVisible();
  await expect(metadata.getByRole("textbox", { name: t["medical.files.description"], exact: true })).toHaveValue("Updated synthetic description");
  await metadata.getByRole("button", { name: t["common.retry"], exact: true }).click();
  await expect(metadata).toHaveCount(0);
  expect(metadataKeys).toHaveLength(2);
  expect(metadataKeys[0]).toBeTruthy();
  expect(metadataKeys[1]).toBe(metadataKeys[0]);
  await expect(files.getByText("Updated synthetic description", { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.history"], exact: true }).click();
  await expect(files.getByRole("button", { name: `${t["medical.clinical.revision"]} 1`, exact: true })).toBeVisible();
  await files.getByRole("button", { name: `${t["medical.clinical.revision"]} 1`, exact: true }).click();
  await expect(files.getByText("Synthetic image for file flow verification", { exact: true })).toBeVisible();
  await expect(files.getByRole("button", { name: t["medical.edit"], exact: true })).toHaveCount(0);
  await files.getByRole("button", { name: `${t["medical.clinical.revision"]} 2`, exact: true }).click();
  await expect(files.getByRole("button", { name: t["medical.edit"], exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
  await expect(image).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await image.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("files-mobile.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await files.getByRole("button", { name: t["medical.edit"], exact: true }).click();
  await metadata.getByRole("textbox", { name: t["medical.reason"], exact: true }).fill("Unsaved mobile reason");
  await metadata.getByRole("button", { name: t["common.cancel"], exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("file-metadata-mobile.png"), fullPage: true });
  page.once("dialog", dialog => dialog.dismiss());
  await metadata.getByRole("button", { name: t["common.cancel"], exact: true }).click();
  await expect(metadata.getByRole("textbox", { name: t["medical.reason"], exact: true })).toHaveValue("Unsaved mobile reason");
  page.once("dialog", dialog => dialog.accept());
  await metadata.getByRole("button", { name: t["common.cancel"], exact: true }).click();
  await expect(metadata).toHaveCount(0);
  await expect(files.getByRole("button", { name: t["medical.edit"], exact: true })).toBeFocused();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await workspace.getByRole("tab", { name: t["medical.tooth.title"], exact: true }).click();
  const chart = workspace.getByTestId("tooth-chart");
  const tooth21 = chart.getByRole("button", { name: `${t["medical.tooth.tooth"]} 21: ${t["medical.tooth.empty"]}`, exact: true });
  await tooth21.click();
  const inspector = page.getByTestId("tooth-inspector");
  await inspector.getByRole("textbox", { name: t["medical.tooth.observation"], exact: true }).fill("Unsaved tooth observation");
  await inspector.getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  const unsaved = page.getByTestId("tooth-unsaved");
  await unsaved.getByRole("button", { name: t["medical.clinical.continueEditing"], exact: true }).click();
  await expect(inspector.getByRole("textbox", { name: t["medical.tooth.observation"], exact: true })).toHaveValue("Unsaved tooth observation");
  await inspector.getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  await unsaved.getByRole("button", { name: t["medical.clinical.leaveUnsaved"], exact: true }).click();
  await expect(workspace.getByRole("tab", { name: t["medical.files.title"], exact: true })).toHaveAttribute("aria-selected", "true");
  const toothFilter = files.getByRole("combobox", { name: new RegExp(`^${t["medical.tooth.tooth"]} `) });
  await expect(toothFilter).toContainText("21");
  await expect(files.getByRole("button", { name: "Synthetic-image.png", exact: true })).toBeEnabled();
  await expect(files.getByRole("button", { name: t["common.refresh"], exact: true })).toBeEnabled();
  await page.screenshot({ path: info.outputPath("files-fdi-desktop.png"), fullPage: true });
  await toothFilter.click();
  await page.getByRole("option", { name: `${t["medical.tooth.tooth"]} 11`, exact: true }).click();
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await toothFilter.click();
  await page.getByRole("option", { name: t["common.all"], exact: true }).click();
  await expect(files.getByRole("button", { name: "Synthetic-image.png", exact: true })).toBeEnabled();
  await workspace.getByRole("tab", { name: t["medical.tooth.title"], exact: true }).click();
  await expect(tooth21).toBeFocused();
  await page.setViewportSize({ width: 390, height: 844 });
  await chart.getByRole("combobox", { name: new RegExp(`^${t["medical.tooth.orientation"]}`) }).click();
  await page.getByRole("option", { name: t["medical.tooth.q2"], exact: true }).click();
  await tooth21.click();
  await inspector.getByRole("button", { name: t["medical.files.title"], exact: true }).click();
  await expect(toothFilter).toContainText("21");
  await expect(files.getByRole("button", { name: t["common.refresh"], exact: true })).toBeEnabled();
  await toothFilter.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("files-fdi-mobile.png"), fullPage: true });
  await files.getByRole("button", { name: "Synthetic-image.png", exact: true }).click();
  await files.getByRole("button", { name: t["medical.files.back"], exact: true }).click();
  let finishRefresh!: () => void;
  const held = new Promise<void>(resolve => { finishRefresh = resolve; });
  await page.route(/\/api\/medical\/files\/\?/, async route => { await held; await route.continue(); });
  await files.getByRole("button", { name: t["common.refresh"], exact: true }).click();
  const fileButton = files.getByRole("button", { name: "Synthetic-image.png", exact: true });
  try { await expect(fileButton).toBeDisabled(); } finally { finishRefresh(); }
  await expect(fileButton).toBeEnabled();
  await fileButton.click();
  await expect(files.getByRole("button", { name: t["medical.files.preview"], exact: true })).toBeEnabled();
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "revoke"], { env: process.env, windowsHide: true, stdio: "pipe" });
  try {
    await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
    await expect(page.getByTestId("clinical-appointment-entry").getByText(t["medical.denied"], { exact: true })).toBeVisible();
    await expect(files).toHaveCount(0);
  } finally {
    execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "restore"], { env: process.env, windowsHide: true, stdio: "pipe" });
  }
});


test("medical files upload recovery: validation, cancel after commit and safe retry", async ({ page }, info) => {
  test.setTimeout(90000);
  const t = ru;
  const appointmentId = newFileAppointment();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await me; await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${appointmentId}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const appointment = await response.json();
  await page.goto(`/app/calendar?appointment=${appointmentId}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`FILES-RECOVERY-${appointmentId}`);
  await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await workspace.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = workspace.getByTestId("medical-files");
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  const description = files.getByRole("textbox", { name: t["medical.files.description"], exact: true });
  const input = files.getByLabel(t["medical.files.file"], { exact: true });
  await description.fill("Retained upload description");
  await input.setInputFiles({ name: "Invalid-image.png", mimeType: "image/png", buffer: Buffer.from("not a PNG") });
  const invalid = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/medical/files/"));
  await files.locator('button[type="submit"]').click();
  expect((await invalid).status()).toBe(400);
  await expect(files.getByRole("alert")).toBeVisible();
  await expect(input).toBeEnabled();
  await expect(description).toHaveValue("Retained upload description");
  await input.setInputFiles({ name: "Recovery-image.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=", "base64") });
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  let saved!: (data: { id: number; replayed: boolean }) => void;
  const committed = new Promise<{ id: number; replayed: boolean }>(resolve => { saved = resolve; });
  const keys: (string | undefined)[] = [];
  page.on("request", request => {
    if (request.method() === "POST" && request.url().endsWith("/api/medical/files/")) keys.push(request.headers()["idempotency-key"]);
  });
  await page.route(/\/api\/medical\/files\/$/, async route => {
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    saved(await response.json());
    await held;
    await route.abort("failed").catch(() => {});
  }, { times: 1 });
  await files.locator('button[type="submit"]').click();
  const first = await committed;
  expect(first.replayed).toBe(false);
  try {
    await files.getByRole("button", { name: t["common.cancel"], exact: true }).click();
    await expect(files.getByText(t["medical.files.interrupted"], { exact: true })).toBeVisible();
  } finally { release(); }
  await expect(description).toHaveValue("Retained upload description");
  await expect(input).toBeDisabled();
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toHaveCount(0);
  await files.getByRole("button", { name: t["common.retry"], exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("upload-interrupted-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await files.getByRole("button", { name: t["common.retry"], exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("upload-interrupted-mobile.png"), fullPage: true });
  const retry = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/medical/files/"));
  await files.getByRole("button", { name: t["common.retry"], exact: true }).click();
  const result = await retry;
  expect(result.status()).toBe(200);
  const replay = await result.json();
  expect(replay.id).toBe(first.id); expect(replay.replayed).toBe(true);
  expect(keys).toHaveLength(2); expect(keys[0]).toBeTruthy(); expect(keys[1]).toBe(keys[0]);
  await expect(files.getByRole("button", { name: "Recovery-image.png", exact: true })).toHaveCount(1);
  await expect(files.getByRole("button", { name: t["common.refresh"], exact: true })).toBeEnabled();
  await files.getByRole("button", { name: "Recovery-image.png", exact: true }).click();
  await expect(files.getByText("Retained upload description", { exact: true })).toBeVisible();
});


test("medical files metadata conflict preserves draft and reloads the winning version", async ({ page }, info) => {
  test.setTimeout(90000);
  const t = ru;
  const appointmentId = newFileAppointment();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await me; await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${appointmentId}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const appointment = await response.json();
  await page.goto(`/app/calendar?appointment=${appointmentId}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`FILES-CONFLICT-${appointmentId}`);
  await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await workspace.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = workspace.getByTestId("medical-files");
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Conflict-image.png", mimeType: "image/png",
    buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=", "base64") });
  await files.getByLabel(t["medical.files.description"], { exact: true }).fill("Original synthetic description");
  await files.locator('button[type="submit"]').click();
  await files.getByRole("button", { name: "Conflict-image.png", exact: true }).click();
  await files.getByRole("button", { name: t["medical.edit"], exact: true }).click();
  const metadata = files.getByTestId("medical-file-metadata");
  const description = metadata.getByRole("textbox", { name: t["medical.files.description"], exact: true });
  const reason = metadata.getByRole("textbox", { name: t["medical.reason"], exact: true });
  await description.fill("My unsaved synthetic description");
  await reason.fill("My retained correction reason");
  await page.route(/\/api\/medical\/files\/\d+\/metadata\//, async route => {
    const winner = await route.fetch({
      headers: { ...route.request().headers(), "idempotency-key": `conflict-winner-${appointmentId}` },
      postData: { ...route.request().postDataJSON(), description: "Winning synthetic description", reason: "Other session saved first" },
    });
    expect(winner.status()).toBe(200);
    expect((await winner.json()).revision).toBe(2);
    await route.continue();
  }, { times: 1 });
  const conflict = page.waitForResponse(r => /\/api\/medical\/files\/\d+\/metadata\//.test(r.url()) && r.status() === 409);
  await metadata.getByRole("button", { name: t["common.save"], exact: true }).click();
  await conflict;
  await expect(metadata.getByRole("alert")).toBeVisible();
  await expect(metadata.getByRole("alert")).toContainText(t["medical.clinical.conflict"]);
  await expect(description).toHaveValue("My unsaved synthetic description");
  await expect(reason).toHaveValue("My retained correction reason");
  await expect(description).toBeEnabled();
  await metadata.getByRole("alert").scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("metadata-conflict-mobile.png") });
  page.once("dialog", dialog => dialog.dismiss());
  await metadata.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(description).toHaveValue("My unsaved synthetic description");
  await expect(reason).toHaveValue("My retained correction reason");
  page.once("dialog", dialog => dialog.accept());
  await metadata.getByRole("button", { name: t["medical.clinical.reload"], exact: true }).click();
  await expect(description).toHaveValue("Winning synthetic description");
  await expect(reason).toHaveValue("");
  await description.fill("Reviewed merged synthetic description");
  await reason.fill("Reviewed the other session's change");
  const saved = page.waitForResponse(r => /\/api\/medical\/files\/\d+\/metadata\//.test(r.url()) && r.status() === 200);
  await metadata.getByRole("button", { name: t["common.save"], exact: true }).click();
  expect((await (await saved).json()).revision).toBe(3);
  await expect(metadata).toHaveCount(0);
  await expect(files.getByText("Reviewed merged synthetic description", { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.history"], exact: true }).click();
  await files.getByRole("button", { name: `${t["medical.clinical.revision"]} 2`, exact: true }).click();
  await expect(files.getByText("Winning synthetic description", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("medical files PDF preview renders locally", async ({ page }, info) => {
  test.setTimeout(90000);
  const t = ru;
  const appointmentId = newFileAppointment();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("medical-role-doctor@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  const login = page.waitForResponse(r => r.url().endsWith("/api/auth/token/") && r.request().method() === "POST");
  const me = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
  await page.locator('form button[type="submit"]').click();
  const token = (await (await login).json()).access;
  await me; await expect(page).toHaveURL(/\/app\//);
  const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/appointments/${appointmentId}/`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(200);
  const appointment = await response.json();
  await page.goto(`/app/calendar?appointment=${appointmentId}&date=${appointment.start_at.slice(0, 10)}&view=day`);
  await openClinicalWorkspace(page);
  const workspace = page.getByTestId("clinical-workspace");
  await workspace.getByLabel(t["medical.clinical.number"], { exact: true }).fill(`FILES-PDF-${appointmentId}`);
  await workspace.getByRole("button", { name: t["medical.clinical.createRecord"], exact: true }).click();
  await workspace.getByRole("button", { name: t["medical.clinical.start"], exact: true }).click();
  await workspace.getByRole("tab", { name: t["medical.files.title"], exact: true }).click();
  const files = workspace.getByTestId("medical-files");
  await expect(files.getByText(t["medical.files.empty"], { exact: true })).toBeVisible();
  await files.getByRole("button", { name: t["medical.files.upload"], exact: true }).click();
  const stream = "BT /F1 24 Tf 40 160 Td (SYNTHETIC PDF PREVIEW) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 480 240] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 480 240] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
    "<< /Length 53 >>\nstream\nBT /F1 24 Tf 40 160 Td (SYNTHETIC SECOND PAGE) Tj ET\nendstream",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => { offsets.push(Buffer.byteLength(pdf)); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${offsets.length}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map(offset => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  await files.getByLabel(t["medical.files.file"], { exact: true }).setInputFiles({ name: "Synthetic-preview.pdf", mimeType: "application/pdf", buffer: Buffer.from(pdf) });
  await files.locator('button[type="submit"]').click();
  await expect(files.getByRole("button", { name: "Synthetic-preview.pdf", exact: true })).toBeEnabled();
  execFileSync(process.env.E2E_PYTHON!, ["e2e/clinical-runtime.py", "files-scan"], { env: process.env, windowsHide: true, stdio: "pipe" });
  await files.getByRole("button", { name: t["common.refresh"], exact: true }).click();
  await files.getByRole("button", { name: "Synthetic-preview.pdf", exact: true }).click();
  await expect(files.getByRole("button", { name: t["medical.files.preview"], exact: true })).toBeEnabled();
  const received = page.waitForResponse(response => /\/api\/medical\/files\/\d+\/preview\//.test(response.url()));
  await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
  expect((await received).status()).toBe(200);
  const viewer = files.getByTestId("medical-pdf-preview");
  await expect(viewer).toHaveAttribute("aria-busy", "false");
  await expect(viewer.getByTestId("medical-pdf-text")).toHaveText("SYNTHETIC PDF PREVIEW");
  const canvas = viewer.getByRole("img", { name: "Synthetic-preview.pdf", exact: true });
  await expect(canvas).toBeVisible();
  expect(await canvas.evaluate((element: HTMLCanvasElement) => {
    const pixels = element.getContext("2d")!.getImageData(0, 0, element.width, element.height).data;
    let ink = 0; for (let i = 0; i < pixels.length; i += 4) if (pixels[i] < 100 && pixels[i + 3] > 0) ink++;
    return ink;
  })).toBeGreaterThan(100);
  await canvas.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("pdf-desktop.png"), fullPage: true });
  await viewer.getByRole("button", { name: t["pagination.next"], exact: true }).click();
  await expect(viewer.getByTestId("medical-pdf-text")).toHaveText("SYNTHETIC SECOND PAGE");
  await expect(viewer.getByRole("button", { name: t["pagination.next"], exact: true })).toBeDisabled();
  await viewer.getByRole("button", { name: t["pagination.previous"], exact: true }).click();
  await expect(viewer.getByTestId("medical-pdf-text")).toHaveText("SYNTHETIC PDF PREVIEW");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(viewer).toHaveAttribute("aria-busy", "false");
  await canvas.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("pdf-mobile.png"), fullPage: true });
  await viewer.getByRole("combobox", { name: new RegExp(`^${t["medical.files.pdfZoom"]}`) }).click();
  await page.getByRole("option", { name: "200%", exact: true }).click();
  await expect(viewer).toHaveAttribute("aria-busy", "false");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.route(/\/api\/medical\/files\/\d+\/preview\//, route => route.fulfill({ status: 200,
    contentType: "application/pdf", body: "%PDF-1.4\nSynthetic invalid PDF" }), { times: 1 });
  await files.getByRole("button", { name: t["medical.files.preview"], exact: true }).click();
  await expect(viewer.getByRole("alert")).toContainText(t["medical.files.pdfError"]);
  await viewer.getByRole("button", { name: t["common.retry"], exact: true }).click();
  await expect(viewer.getByTestId("medical-pdf-text")).toHaveText("SYNTHETIC PDF PREVIEW");
  await workspace.getByRole("tab", { name: t["medical.clinical.history"], exact: true }).click();
  await expect(viewer).toHaveCount(0);

});
