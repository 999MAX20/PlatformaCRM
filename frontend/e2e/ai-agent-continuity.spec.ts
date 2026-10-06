import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import type { Bot } from "../src/types";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated synthetic fixtures");
  test.setTimeout(180_000);
});

test("conversation persists, failed send preserves its key, reset and archive retain history", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = (await session.list<Bot>("bots")).find(item => item.scenario === "crm") || await session.create<Bot>("bots", { name: "Conversation acceptance", scenario: "crm" });
  if (bot.status !== "active") await session.action(`bots/${bot.id}/activate`);
  await page.goto(`/app/ai-agents/${bot.id}/work`);
  const panel = page.getByRole("region", { name: "Диалог с агентом", exact: true });
  const input = panel.getByRole("textbox", { name: "Сообщение агенту", exact: true });
  await input.fill("Какие задачи доступны сейчас?");
  let failedKey = "";
  let acceptedKey = "";
  let attempts = 0;
  await page.route("**/api/ai/conversations/*/turns/", async route => {
    attempts++;
    const key = route.request().postDataJSON().idempotency_key;
    if (attempts === 1) { failedKey = key; await route.fulfill({ status: 503, json: { detail: "Synthetic unavailable response" } }); }
    else { acceptedKey = key; await route.continue(); }
  });
  await panel.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(input).toHaveValue("Какие задачи доступны сейчас?");
  await panel.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(input).toHaveValue("");
  expect(attempts).toBe(2);
  expect(acceptedKey).toBe(failedKey);
  await expect(panel.getByLabel("Сообщения диалога").getByText("Какие задачи доступны сейчас?", { exact: true })).toBeVisible();
  const id = new URL(page.url()).searchParams.get("agent_thread")!;
  await page.reload();
  await expect(panel.getByLabel("Сообщения диалога").getByText("Какие задачи доступны сейчас?", { exact: true })).toBeVisible();
  expect((await session.read(`ai/conversations/${id}`)).turns).toHaveLength(1);
  await panel.getByRole("button", { name: "Очистить память", exact: true }).click();
  await page.getByRole("dialog", { name: "Очистить память", exact: true }).getByRole("button", { name: "Очистить память", exact: true }).click();
  await expect.poll(async () => (await session.read(`ai/conversations/${id}`)).conversation.memory_epoch).toBe(1);
  await expect(panel.getByLabel("Сообщения диалога").getByText("Какие задачи доступны сейчас?", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "В архив", exact: true }).click();
  await page.getByRole("dialog", { name: "В архив", exact: true }).getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(input).toHaveCount(0);
  await panel.getByRole("button", { name: "Восстановить", exact: true }).click();
  await page.getByRole("dialog", { name: "Восстановить", exact: true }).getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(input).toBeVisible();
  for (const [locale, label] of [["ru", "Диалог с агентом"], ["kk", "Агентпен диалог"], ["en", "Agent conversation"]]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.reload();
    const current = page.getByRole("region", { name: label, exact: true });
    await expect(current.getByRole("textbox")).toBeVisible();
    await current.getByRole("textbox").focus();
    await expect(current.getByRole("textbox")).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    expect((await new AxeBuilder({ page }).include('[data-testid="ai-agent-editor"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: info.outputPath(`conversation-${locale}.png`), fullPage: true });
  }
});

test("reviewed action UI supports explicit confirmation, interrupted progress and safe retry", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = (await session.list<Bot>("bots")).find(item => item.scenario === "crm") || await session.create<Bot>("bots", { name: "Conversation actions", scenario: "crm" });
  if (bot.status !== "active") await session.action(`bots/${bot.id}/activate`);
  const thread = await session.create<{ id: string }>("ai/conversations", { agent: bot.id });
  const saved = (await session.read(`ai/conversations/${thread.id}`)).conversation;
  const action = { id: 123456, business: session.business, user: session.userId, tool_name: "crm_create", status: "suggested", fingerprint: "a".repeat(64), input_json: { entity: "tasks", values: { title: "Synthetic reviewed task" } }, output_json: {}, error: "", created_at: new Date().toISOString() };
  let turn = { id: 987654, sequence: 1, status: "awaiting_confirmation", mode: "work", message: "Prepare two tasks", response: "Проверьте предложенные действия и подтвердите выполнение.", redacted: false, sources: [], actions: [action], total_steps: 2, completed_steps: 0, created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
  let confirmations = 0;
  let retries = 0;
  // This test covers UI contracts with controlled responses. Domain execution,
  // idempotency and rollback are verified by tests_conversation_execution.
  await page.route(`**/api/ai/conversations/${thread.id}/`, route => route.fulfill({ json: { conversation: { ...saved, revision: 1 }, turns: [turn], has_more: false, next_before: 1 } }));
  await page.route(`**/api/ai/conversations/${thread.id}/turns/${turn.id}/confirm/`, async route => {
    confirmations++;
    expect(route.request().postDataJSON()).toEqual({ expected_revision: 1, actions: [{ id: action.id, fingerprint: action.fingerprint }] });
    turn = { ...turn, status: "failed", completed_steps: 1, response: "Часть действий выполнена.", actions: [{ ...action, status: "executed" }] };
    await route.fulfill({ json: turn });
  });
  await page.route(`**/api/ai/conversations/${thread.id}/turns/${turn.id}/retry/`, async route => {
    retries++;
    expect(route.request().postDataJSON().idempotency_key).toBeTruthy();
    turn = { ...turn, status: "clarifying", response: "Как назвать вторую задачу?" };
    await route.fulfill({ json: turn });
  });
  await page.goto(`/app/ai-agents/${bot.id}/work?agent_thread=${thread.id}`);
  const panel = page.getByRole("region", { name: "Диалог с агентом", exact: true });
  await expect(panel.getByRole("table")).toContainText("Synthetic reviewed task");
  await panel.getByRole("button", { name: "Подтвердить действия", exact: true }).click();
  const confirm = page.getByRole("dialog", { name: "Выполнить проверенное действие?" });
  await confirm.getByRole("button", { name: "Отмена", exact: true }).click();
  expect(confirmations).toBe(0);
  await panel.getByRole("button", { name: "Подтвердить действия", exact: true }).click();
  await confirm.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(panel.getByText("Выполнено 1 из 2", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "Повторить оставшееся", exact: true }).click();
  await expect(panel.getByText("Как назвать вторую задачу?", { exact: true })).toBeVisible();
  expect(confirmations).toBe(1); expect(retries).toBe(1);
  await page.screenshot({ path: info.outputPath("action-progress.png"), fullPage: true });
});
