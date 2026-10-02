import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { crmSession } from "./support/crm-workspace";
import type { Client } from "../src/types";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
test.beforeEach(({}, info) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated API fixtures");
  test.skip(info.project.name === "tablet-chromium", "Desktop and mobile cover these flows");
  test.setTimeout(120_000);
});

test("AI CRM search prepares exact change, preserves failure draft and executes only after confirmation", async ({ page }, info) => {
  const session = await crmSession(page);
  const name = `AI history ${info.project.name}`;
  const person = await session.create<Client>("clients", { full_name: name, source: "manual" });
  await page.goto("/app/ai-assistant");
  const panel = page.getByRole("region", { name: "Действия с CRM", exact: true });
  // The source lookup and command log use the real isolated API; only model output is controlled.
  await panel.getByLabel("Поиск", { exact: true }).fill(name);
  await page.getByLabel("Запись для действия", { exact: true }).click();
  await page.getByRole("option", { name: `${name} · #${person.id}`, exact: true }).click();
  const instruction = `Измени имя на ${name} reviewed`;
  await page.getByRole("textbox", { name: "Что нужно сделать?", exact: true }).fill(instruction);
  await page.route("**/api/ai/crm/plan/", route => route.fulfill({ status: 503, json: { detail: "Synthetic provider failure" } }));
  await page.getByRole("button", { name: "Подготовить действие", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Что нужно сделать?", exact: true })).toHaveValue(instruction);
  await expect(page.getByRole("alert").last()).toBeVisible();
  await page.unroute("**/api/ai/crm/plan/");
  await page.route("**/api/ai/crm/plan/", async route => {
    const result = await session.action("ai/tools/suggest", { business: session.business, tool_name: "crm_update", arguments: { entity: "clients", entity_id: person.id, values: { full_name: `${name} reviewed` } } });
    await route.fulfill({ json: { question: "", suggested_actions: result.suggested_actions } });
  });
  await page.getByRole("button", { name: "Подготовить действие", exact: true }).click();
  const review = page.getByRole("region", { name: "Проверка действия" });
  await expect(review).toContainText(`${name} reviewed`);
  expect((await session.read(`clients/${person.id}`)).full_name).toBe(name);
  await panel.screenshot({ path: info.outputPath("crm-reviewed-command.png") });
  await review.getByRole("button", { name: "Подтвердить", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Выполнить проверенное действие?" });
  await expect(dialog).toBeVisible();
  expect((await session.read(`clients/${person.id}`)).full_name).toBe(name);
  await dialog.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(review).toContainText("Действие выполнено");
  expect((await session.read(`clients/${person.id}`)).full_name).toBe(`${name} reviewed`);
  await expect(page.locator("body")).not.toContainText("expected_version");
});

test("business financial source persists and historical report uses real journal totals", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.goto("/app/settings#business-profile");
  await page.getByLabel("Источник финансового анализа", { exact: true }).click();
  await page.getByRole("option", { name: "Ручной учёт CRM", exact: true }).click();
  const saved = page.waitForResponse(response => response.url().endsWith(`/api/businesses/${session.business}/`) && response.request().method() === "PATCH");
  await page.locator("#business-profile form button[type=submit]").click();
  expect((await saved).status()).toBe(200);
  await page.reload();
  await expect(page.getByLabel("Источник финансового анализа", { exact: true })).toContainText("Ручной учёт CRM");
  const baseline = await session.read("ai/analyst/history", { business: session.business, start: "2025-04-01", end: "2025-04-30" });
  const client = await session.create<Client>("clients", { full_name: `Cash history ${info.project.name}` });
  const receipt = await session.create<{ id: number }>("client-payments", { client: client.id, amount: "100.25", currency: "KZT", occurred_at: "2025-04-15T10:00:00Z", method: "cash", submission_id: randomUUID() });
  await session.create("client-payments", { original: receipt.id, amount: "20.25", reason: "Synthetic return", occurred_at: "2025-04-16T10:00:00Z", method: "cash", submission_id: randomUUID() });
  await page.goto("/app/ai-assistant");
  await page.getByLabel("Начало периода", { exact: true }).fill("2025-04-01");
  await page.getByLabel("Конец периода", { exact: true }).fill("2025-04-30");
  const reportResponse = page.waitForResponse(response => response.url().includes("/api/ai/analyst/history/") && response.url().includes("2025-04-01"));
  await page.getByRole("button", { name: "Показать", exact: true }).click();
  const report = await (await reportResponse).json();
  expect(report.financial.source.provider).toBe("manual");
  expect(Number(report.financial.net_receipts)).toBe(Number(baseline.financial.net_receipts) + 80);
  const table = page.getByRole("table", { name: "Поступления и возвраты за период" });
  await expect(table).toContainText("Поступления − возвраты");
  await expect(page.getByText("Прибыль и задолженность недоступны:", { exact: false })).toBeVisible();
  await page.getByText("Динамика поступлений и возвратов", { exact: true }).click();
  await expect(page.getByRole("cell", { name: "2025-04-15", exact: true }).or(page.getByRole("rowheader", { name: "2025-04-15", exact: true }))).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  await page.getByRole("heading", { name: "История и финансовый анализ", exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("history-manual-finance.png") });
  const restore = await page.request.patch(`${api}/api/businesses/${session.business}/`, { headers: session.headers, data: { financial_source_mode: "external", financial_connector: null } });
  expect(restore.ok()).toBeTruthy();
});

test("CRM and history controls remain reachable by keyboard in RU KK EN", async ({ page }, info) => {
  await crmSession(page);
  for (const [locale, crmTitle, historyTitle, search, clients, receipts] of [
    ["ru", "Действия с CRM", "История и финансовый анализ", "Поиск", "Клиенты", "Поступления"],
    ["kk", "CRM әрекеттері", "Тарих және қаржылық талдау", "Іздеу", "Клиенттер", "Түсімдер"],
    ["en", "CRM actions", "History and financial analysis", "Search", "Clients", "Receipts"],
  ]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/ai-assistant");
    const panel = page.getByRole("region", { name: crmTitle, exact: true });
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("combobox").first()).toContainText(clients);
    await panel.getByRole("textbox", { name: search, exact: true }).focus();
    await expect(panel.getByRole("textbox", { name: search, exact: true })).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(panel.getByRole("checkbox")).toBeFocused();
    await expect(page.getByRole("region", { name: historyTitle, exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: historyTitle, exact: true }).getByRole("rowheader", { name: receipts, exact: true })).toBeVisible();
    await expect(panel).not.toContainText("aiCRM.");
    await panel.screenshot({ path: info.outputPath(`crm-${locale}.png`) });
  }
});

test("changed CRM target is rejected after review and does not overwrite staff work", async ({ page }) => {
  const session = await crmSession(page);
  const client = await session.create<Client>("clients", { full_name: `Stale review ${randomUUID()}` });
  const result = await session.action("ai/tools/suggest", { business: session.business, tool_name: "crm_update", arguments: { entity: "clients", entity_id: client.id, values: { full_name: "Obsolete proposal" } } });
  await page.goto("/app/ai-assistant");
  await page.getByRole("textbox", { name: "Что нужно сделать?", exact: true }).fill("Change reviewed name");
  await page.route("**/api/ai/crm/plan/", route => route.fulfill({ json: { question: "", suggested_actions: result.suggested_actions } }));
  await page.getByRole("button", { name: "Подготовить действие", exact: true }).click();
  const changed = await page.request.patch(`${api}/api/clients/${client.id}/`, { headers: session.headers, data: { full_name: "Staff latest value" } });
  expect(changed.ok()).toBeTruthy();
  const review = page.getByRole("region", { name: "Проверка действия" });
  await review.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.getByRole("alert").last()).toBeVisible();
  expect((await session.read(`clients/${client.id}`)).full_name).toBe("Staff latest value");
});
