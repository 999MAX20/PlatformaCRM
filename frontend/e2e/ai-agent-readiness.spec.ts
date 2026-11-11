import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import type { AgentProfile, Bot, BotChannel } from "../src/types";

const api = process.env.E2E_API_BASE_URL;
let createdBots: number[] = [];
let ownerHeaders: Record<string, string> = {};
async function ownerSession(page: Page) {
  const session = await crmSession(page);
  ownerHeaders = session.headers;
  return session;
}
function remember(bot: Bot) { createdBots.push(bot.id); return bot; }
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated fixtures and mock AI");
  test.setTimeout(180_000);
  createdBots = [];
});
test.afterEach(async ({ page }) => {
  for (const id of createdBots) {
    const response = await page.request.delete(`${api}/api/bots/${id}/`, { headers: ownerHeaders });
    expect(response.status(), await response.text()).toBe(204);
  }
});

test("saved capability is distinguished from effective mode and server model persists", async ({ page }, info) => {
  const session = await ownerSession(page);
  const bot = remember(await session.create<Bot>("bots", { name: "Readiness customer", scenario: "inbox" }));
  await session.create("ai/agent-profiles", { bot: bot.id, name: bot.name, allowed_tools_json: { tools: ["create_lead"] } });
  await page.goto(`/app/ai-agents/${bot.id}/actions`);
  const editor = page.getByTestId("ai-agent-editor");
  const savedOnly = editor.getByText("Разрешено, не действует", { exact: true });
  await expect(savedOnly).toHaveCount(1);
  await expect(editor.getByText("Разрешение сохранено, но выбранный режим не допускает это действие.")).toBeVisible();
  await editor.getByLabel("Что делать после диалога", { exact: true }).click();
  await page.getByRole("option", { name: "Заявки и задачи", exact: true }).click();
  await expect(savedOnly).toHaveCount(0);
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  expect((await session.read(`bots/${bot.id}`)).settings_json.auto_crm_pipeline.mode).toBe("lead_task");
  await editor.getByLabel("Что делать после диалога", { exact: true }).click();
  await page.getByRole("option", { name: "Только оценить обращение", exact: true }).click();
  await expect(savedOnly).toHaveCount(1);
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  const profiles = await session.list<AgentProfile>("ai/agent-profiles");
  expect(profiles.find(item => item.bot === bot.id)?.allowed_tools_json.tools).toContain("create_lead");
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await editor.locator("summary").filter({ hasText: "Дополнительные настройки" }).click();
  await editor.getByLabel("Режим ответов", { exact: true }).click();
  await page.getByRole("option", { name: "Максимальное качество", exact: true }).click();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  const saved = await session.read(`bots/${bot.id}`);
  expect(saved.settings_json.model).toBe(saved.readiness.provider.model_options[0].value);
  await expect(page.getByTestId("agent-readiness")).toContainText("Тестовый AI");
  await page.screenshot({ path: info.outputPath("customer-readiness-profile.png"), fullPage: true });
});

test("agent activity has scoped counts, error recovery and links ignore stale inbox filters", async ({ page }, info) => {
  const session = await ownerSession(page);
  const bot = remember(await session.create<Bot>("bots", { name: "Activity customer", scenario: "inbox" }));
  const other = remember(await session.create<Bot>("bots", { name: "Unrelated customer", scenario: "inbox" }));
  for (const agent of [bot, other]) await session.create("ai/agent-profiles", { bot: agent.id, name: agent.name });
  await page.goto(`/app/ai-agents/${bot.id}/test`);
  const activity = page.getByTestId("agent-activity");
  await expect(activity.getByText(/Доступных диалогов пока нет/)).toBeVisible();
  for (const agent of [bot, other]) {
    const channel = await session.create<BotChannel>("bot-channels", { bot: agent.id, channel: "website" });
    const enabled = await page.request.patch(`${api}/api/bot-channels/${channel.id}/`, { headers: session.headers, data: { status: "active" } });
    expect(enabled.ok(), await enabled.text()).toBeTruthy();
    const conversation = await page.request.post(`${api}/api/public/website-chat/${channel.public_token}/conversations/`,
      { data: { message: "Synthetic readiness conversation", external_user_id: `readiness-${agent.id}` } });
    expect(conversation.status(), await conversation.text()).toBe(201);
  }
  await page.route("**/api/inbox/conversations/summary/?bot=*", route => route.fulfill({ status: 503, json: { detail: "Synthetic summary failure" } }));
  await page.reload();
  await expect(activity.getByRole("button", { name: "Повторить", exact: true })).toBeVisible();
  await page.unroute("**/api/inbox/conversations/summary/?bot=*");
  await activity.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(activity.getByRole("link", { name: "Всего диалогов: 1", exact: true })).toBeVisible();
  await expect(activity.getByRole("link", { name: "С непрочитанными: 1", exact: true })).toHaveAttribute("href", `/app/conversations?bot=${bot.id}&preset=all&status=open&unread=true`);
  await expect(activity.getByRole("link", { name: "Ожидают сотрудника: 0", exact: true })).toHaveAttribute("href", `/app/conversations?bot=${bot.id}&preset=all&status=open&handoff_required=true`);
  await page.screenshot({ path: info.outputPath("customer-activity.png"), fullPage: true });
  await page.evaluate(() => localStorage.setItem("zani_conversations_filters_v1", JSON.stringify({ preset: "custom", filters: { channel: "telegram", priority: "urgent" } })));
  const inbox = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === "/api/inbox/conversations/" && url.searchParams.get("bot") === String(bot.id);
  });
  await activity.getByRole("link", { name: "Всего диалогов: 1", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/conversations\\?bot=${bot.id}&preset=all$`));
  const response = await inbox;
  expect(new URL(response.url()).searchParams.has("channel")).toBe(false);
  const payload = await response.json();
  expect(payload.results.length).toBe(1);
  expect(payload.results[0].bot).toBe(bot.id);
});

test("CRM operations recover from status failure and disabled analytics sends no analysis requests", async ({ page }, info) => {
  const session = await ownerSession(page);
  let bot = (await session.list<Bot>("bots")).find(item => item.scenario === "crm");
  if (!bot) bot = remember(await session.create<Bot>("bots", { name: "Readiness CRM", scenario: "crm" }));
  const profile = (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot!.id)!;
  const update = await page.request.put(`${api}/api/bots/${bot.id}/configuration/`, { headers: session.headers,
    data: { bot: { settings_json: bot.settings_json }, profile: { id: profile.id, rules_json: { sources: ["tasks"], analyst_enabled: false }, allowed_tools_json: { tools: ["crm_read"] } } } });
  expect(update.ok(), await update.text()).toBeTruthy();
  if (bot.status !== "active") await session.action(`bots/${bot.id}/activate`);
  await page.route("**/api/ai/assistant/status/**", route => route.fulfill({ status: 503, json: { detail: "Synthetic status failure" } }));
  await page.goto(`/app/ai-agents/${bot.id}/work`);
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByText("Не удалось загрузить доступные операции CRM.", { exact: true })).toBeVisible();
  await page.unroute("**/api/ai/assistant/status/**");
  await editor.getByRole("button", { name: "Повторить", exact: true }).last().click();
  await expect(editor.getByText("Не удалось загрузить доступные операции CRM.", { exact: true })).toHaveCount(0);
  await expect(editor.locator("summary").filter({ hasText: "Действия с CRM" })).toBeVisible();
  let analysisRequests = 0;
  page.on("request", request => { if (/\/api\/ai\/(analyst|history|conversations)/.test(request.url())) analysisRequests++; });
  await editor.getByRole("tab", { name: "Аналитика", exact: true }).click();
  await expect(editor.getByText("Аналитика отключена в настройках агента.", { exact: true })).toBeVisible();
  await expect(editor.getByRole("textbox", { name: "Сообщение агенту", exact: true })).toHaveCount(0);
  expect(analysisRequests).toBe(0);
  await editor.getByRole("link", { name: "Действия", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/${bot.id}/actions$`));
  await editor.getByRole("switch", { name: "Разрешить аналитику", exact: true }).check();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  await editor.getByRole("tab", { name: "Аналитика", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Вопрос по выбранному периоду", exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("crm-analytics-restored.png"), fullPage: true });
});

test("provider limitation and booking warnings remain readable in RU KK EN at desktop and mobile widths", async ({ page }, info) => {
  const session = await ownerSession(page);
  const bot = remember(await session.create<Bot>("bots", { name: "Provider unavailable", scenario: "inbox" }));
  await session.create("ai/agent-profiles", { bot: bot.id, name: bot.name });
  await page.route("**/api/bots/**", async route => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const payload = await response.json();
    const items: Bot[] = Array.isArray(payload) ? payload : payload.results || [payload];
    for (const item of items) if (item.id === bot.id && item.readiness?.provider) {
      item.readiness.is_ready = false;
      item.readiness.provider.state = "not_configured";
      item.readiness.provider.configuration_ready = false;
      item.readiness.booking = { enabled: true, setup_ready: false, missing: ["responsible", "authorization"] };
    }
    await route.fulfill({ response, json: payload });
  });
  for (const [locale, width] of [["ru", 1440], ["kk", 320], ["en", 390]] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/ai-agents/${bot.id}/profile`);
    const editor = page.getByTestId("ai-agent-editor");
    const status = page.getByTestId("agent-readiness");
    await expect(status).toBeVisible();
    await expect(status).toContainText(locale === "ru" ? "AI-провайдер не настроен" : locale === "kk" ? "AI провайдері бапталмаған" : "The AI provider is not configured");
    await expect(editor.getByRole("switch").first()).toBeDisabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    expect((await new AxeBuilder({ page }).include('[data-testid="agent-readiness"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: info.outputPath(`readiness-${locale}-${width}.png`), fullPage: true });
  }
});
