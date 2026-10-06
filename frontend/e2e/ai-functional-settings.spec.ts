import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { AgentProfile, Bot } from "../src/types";
const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

test.beforeEach(({}, info) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated API fixtures");
  test.skip(info.project.name === "tablet-chromium", "Desktop and mobile cover this flow");
  test.setTimeout(120_000);
});

test("saved messenger capabilities survive reload and are atomic on API failure", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Functional messenger", status: "draft" });
  await session.create<AgentProfile>("ai/agent-profiles", { bot: bot.id, name: "Functional messenger", allowed_tools_json: { tools: ["handoff_to_manager"] } });
  await page.goto(`/app/ai-agents/${bot.id}/actions`);
  const editor = page.getByTestId("ai-agent-editor");
  await editor.getByLabel("Что делать после диалога", { exact: true }).click();
  await page.getByRole("option", { name: "Заявки и задачи", exact: true }).click();
  await editor.getByLabel("Создание новых записей", { exact: true }).click();
  await page.getByRole("option", { name: "Автоматически по разрешению бизнеса", exact: true }).click();
  await editor.getByRole("switch", { name: "Создать заявку", exact: true }).click();
  const saved = page.waitForResponse(response => response.url().endsWith(`/bots/${bot.id}/configuration/`) && response.request().method() === "PUT");
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  expect((await saved).status()).toBe(200);
  const readback = await session.read(`bots/${bot.id}`);
  expect(readback.settings_json.auto_crm_pipeline.creation_policy).toBe("automatic");
  await page.reload();
  await expect(editor.getByLabel("Создание новых записей", { exact: true })).toContainText("Автоматически по разрешению бизнеса");
  await expect(editor.getByRole("switch", { name: "Создать заявку", exact: true })).toHaveAttribute("aria-checked", "true");
  await page.screenshot({ path: info.outputPath("messenger-capabilities.png"), fullPage: true });
  await page.route(`**/api/bots/${bot.id}/configuration/`, route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic save failure" }) }));
  await editor.getByRole("switch", { name: "Создать заявку", exact: true }).click();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("alert").first()).toBeVisible();
  await expect(editor.getByRole("switch", { name: "Создать заявку", exact: true })).toHaveAttribute("aria-checked", "false");
  const profiles = await session.list<AgentProfile>("ai/agent-profiles");
  expect(profiles.find(item => item.bot === bot.id)?.allowed_tools_json.tools).toContain("create_lead");
  await page.unroute(`**/api/bots/${bot.id}/configuration/`);
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  expect((await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)?.allowed_tools_json.tools).not.toContain("create_lead");
});

test("CRM agent source controls persist and pause revokes runtime", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "CRM settings", scenario: "crm" });
  await session.action(`bots/${bot.id}/activate`);
  await page.goto(`/app/ai-agents/${bot.id}/knowledge`);
  const editor = page.getByTestId("ai-agent-editor");
  await editor.getByLabel("Клиенты", { exact: true }).uncheck();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect.poll(async () => (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)?.rules_json.sources).not.toContain("clients");
  await page.reload();
  await expect(editor.getByLabel("Клиенты", { exact: true })).not.toBeChecked();
  await editor.getByRole("switch", { name: "Изменить статус агента CRM settings" }).click();
  await expect.poll(async () => (await session.read(`bots/${bot.id}`)).status).toBe("paused");
  const blocked = await page.request.post(`${api}/api/ai/tools/suggest/`, { headers: session.headers, data: { business: session.business, agent: bot.id, message: "Follow up" } });
  expect(blocked.status()).toBe(403);
  await editor.getByRole("tab", { name: "Работа с CRM", exact: true }).click();
  await expect(editor.getByText(/Агент ещё не активен/)).toBeVisible();
  await page.screenshot({ path: info.outputPath("crm-paused.png"), fullPage: true });
});
