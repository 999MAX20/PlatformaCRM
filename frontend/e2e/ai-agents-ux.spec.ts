import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Bot, BusinessKnowledgeItem } from "../src/types";

const cleanupAgents: Array<() => Promise<void>> = [];
async function createAgent(page: Page, session: Awaited<ReturnType<typeof crmSession>>, data: Record<string, unknown>) {
  const bot = await session.create<Bot>("bots", data);
  cleanupAgents.push(async () => {
    const response = await page.request.delete(`${process.env.E2E_API_BASE_URL}/api/bots/${bot.id}/`, { headers: session.headers });
    expect(response.ok(), await response.text()).toBeTruthy();
  });
  return bot;
}

test.afterEach(async () => {
  for (const cleanup of cleanupAgents.splice(0)) await cleanup();
});

async function openSection(page: Page, label: string) {
  const navigation = page.getByRole("navigation", { name: "Разделы редактора агента" });
  const section = navigation.locator("#agent-section-links").getByRole("button", { name: label, exact: true });
  if (!await section.isVisible()) await navigation.locator(":scope > button").click();
  await section.click();
}

async function choose(page: Page, label: string, option: string) {
  await page.getByRole("combobox", { name: new RegExp(`^${label} `) }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable API fixtures");
  test.setTimeout(120_000);
});

test("visible instructions, deliberate template and navigation draft protection", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: `UX ${info.project.name}`, status: "draft" });
  await session.create("ai/agent-profiles", { bot: bot.id, name: "Legacy profile name", is_active: true, role_description: "Existing role", system_prompt: "Keep this instruction", allowed_tools_json: { tools: [] } });
  await page.goto(`/app/ai-agents/${bot.id}/instructions`);
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toBeVisible();
  await expect(editor.getByLabel("Название профиля", { exact: true })).toHaveCount(0);
  await editor.getByRole("button", { name: "Шаблон: администратор бизнеса", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/Он заменит описание роли/)).toBeVisible();
  await dialog.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Keep this instruction");
  await editor.getByRole("button", { name: "Шаблон: администратор бизнеса", exact: true }).click();
  await dialog.getByRole("button", { name: "Заполнить по шаблону" }).click();
  await expect(editor.getByRole("textbox", { name: "Описание роли", exact: true })).toHaveValue("Администратор бизнеса");
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue(/Ты администратор бизнеса\./);
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue(/Не ставь диагнозы и не назначай лечение/);
  await page.locator('a[href="/app/conversations"]:visible').first().click();
  await expect(page.getByRole("dialog", { name: "Несохранённые изменения" })).toBeVisible();
  await dialog.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).not.toHaveValue("Keep this instruction");
  await page.locator('a[href="/app/conversations"]:visible').first().click();
  await dialog.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/conversations(?:\?|$)/);
  await page.goto(`/app/ai-agents/${bot.id}/instructions`);
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Keep this instruction");
  await page.screenshot({ path: info.outputPath("profile-template-guard.png"), fullPage: true });
});

test("knowledge explains requirements, rejects whitespace, retains failed save and persists retry", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Knowledge UX", status: "draft" });
  await page.goto(`/app/ai-agents/${bot.id}/knowledge`);
  await page.getByRole("button", { name: "Добавить знание", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Для сохранения заполните название и содержание.")).toBeVisible();
  await dialog.getByRole("textbox", { name: /^Содержание/ }).fill("  ");
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(dialog.getByText("Укажите название знания.")).toBeVisible();
  await expect(dialog.getByText("Добавьте содержание знания.")).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: /^Название/ })).toBeFocused();
  const title = `Knowledge ${info.project.name} ${Date.now()}`;
  await dialog.getByRole("textbox", { name: /^Название/ }).fill(title);
  await dialog.getByRole("textbox", { name: /^Содержание/ }).fill("Company reference content");
  await page.route("**/api/ai/knowledge-items/", route => route.request().method() === "POST" ? route.fulfill({ status: 503, json: { detail: "Synthetic failure" } }) : route.continue());
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(dialog.getByRole("alert").first()).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: /^Название/ })).toHaveValue(title);
  await page.unroute("**/api/ai/knowledge-items/");
  await dialog.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(dialog).toBeHidden();
  expect((await session.read("ai/knowledge-items", { agent: bot.id })).results.some((item: BusinessKnowledgeItem) => item.title === title && item.bot === bot.id)).toBeTruthy();
  await page.screenshot({ path: info.outputPath("knowledge-saved.png"), fullPage: true });
});

test("agent configuration recovers from a failed load and stays unavailable to managers", async ({ page }) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Recovery", status: "draft" });
  await page.route("**/api/ai/agent-profiles/", route => route.fulfill({ status: 503, json: { detail: "Synthetic failure" } }));
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await expect(page.getByRole("alert").first()).toBeVisible();
  await expect(page.getByTestId("ai-agent-editor")).toHaveCount(0);
  await page.unroute("**/api/ai/agent-profiles/");
  await page.getByRole("button", { name: "Повторить", exact: true }).first().click();
  await expect(page.getByTestId("ai-agent-editor")).toBeVisible();
  await page.context().clearCookies();
  await page.evaluate(() => localStorage.clear());
  await crmSession(page, "business_manager@example.com");
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await expect(page.getByText("CRM-агент ещё не создан. Обратитесь к владельцу компании.")).toBeVisible();
  await expect(page.getByTestId("ai-agent-editor")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Новый агент", exact: true })).toHaveCount(0);
});

test("configuration survives section changes and a failed atomic save", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Сохранение настроек", status: "draft", settings_json: { memory_enabled: true, temperature: 0.4 } });
  await session.create("ai/agent-profiles", {
    bot: bot.id, name: bot.name, is_active: true, role_description: "Исходная роль", system_prompt: "Исходная инструкция",
    rules_json: { items: ["Исходное правило"], retained_setting: "keep" }, allowed_tools_json: { tools: ["create_client", "handoff_to_manager"] },
    escalation_rules_json: { items: ["Исходная передача"] },
  });
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await expect(page.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveCount(0);
  await page.getByRole("textbox", { name: "Название", exact: true }).fill("Сохранённый агент");
  await choose(page, "Язык", "English");
  await choose(page, "Тон", "Формальный");
  await openSection(page, "Инструкции");
  await expect(page.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Исходная инструкция");
  await page.getByRole("textbox", { name: "Описание роли", exact: true }).fill("Новая роль");
  await page.getByRole("textbox", { name: "Главная инструкция", exact: true }).fill("Новая инструкция");
  await page.getByRole("textbox", { name: "Правила", exact: true }).fill("Новое правило");
  await page.getByRole("button", { name: "Тестовый чат", exact: true }).click();
  const preview = page.getByTestId("agent-preview-panel");
  await expect(preview).toBeVisible();
  await expect(preview.getByRole("button", { name: "Проверить ответ", exact: true })).toBeDisabled();
  await preview.getByRole("button", { name: "Закрыть", exact: true }).click();
  await openSection(page, "Дополнительно");
  await page.getByRole("switch", { name: "Память диалогов", exact: true }).click();
  await page.getByRole("slider").press("End");
  await openSection(page, "Действия");
  await choose(page, "Что делать после диалога", "Только оценить обращение");
  const configurationUrl = `**/api/bots/${bot.id}/configuration/`;
  await page.route(configurationUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic configuration failure" } }));
  await page.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(page.getByRole("alert").first()).toBeVisible();
  await openSection(page, "Инструкции");
  await expect(page.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Новая инструкция");
  await page.unroute(configurationUrl);
  const saved = page.waitForResponse(response => response.request().method() === "PUT" && response.url().endsWith(`/bots/${bot.id}/configuration/`));
  await page.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  expect((await saved).ok()).toBeTruthy();
  await expect(page.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  const persisted = await session.read(`bots/${bot.id}`);
  expect(persisted).toMatchObject({ name: "Сохранённый агент", status: "draft", default_language: "en", settings_json: { memory_enabled: false, temperature: 1, auto_crm_pipeline: { mode: "triage" } } });
  const profiles = (await session.read("ai/agent-profiles")).results;
  expect(profiles.find((profile: { bot: number }) => profile.bot === bot.id)).toMatchObject({
    role_description: "Новая роль", system_prompt: "Новая инструкция", tone: "formal",
    rules_json: { items: ["Новое правило"], retained_setting: "keep" },
    allowed_tools_json: { tools: ["create_client", "handoff_to_manager"] }, escalation_rules_json: { items: ["Исходная передача"] },
  });
  await page.screenshot({ path: info.outputPath("instructions-save-recovery.png"), fullPage: true });
});

test("new profile state, aliases and agent switching retain deliberate draft guards", async ({ page }) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Новый профиль", status: "draft" });
  const other = await createAgent(page, session, { name: "Другой агент", status: "draft" });
  await session.create("ai/agent-profiles", { bot: other.id, name: other.name, is_active: true, system_prompt: "Сохранённая инструкция" });
  await page.goto(`/app/ai-agents/${bot.id}`);
  await expect(page).toHaveURL(new RegExp(`/${bot.id}/profile$`));
  await expect(page.getByTestId("agent-save-bar")).toContainText("Профиль ещё не сохранён");
  await expect(page.getByTestId("agent-save-bar")).not.toContainText("Есть несохранённые изменения");
  await page.getByRole("textbox", { name: "Название", exact: true }).fill("Черновик названия");
  await openSection(page, "Инструкции");
  await openSection(page, "Профиль");
  await expect(page.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Черновик названия");
  await page.getByTestId("agent-picker-trigger").click();
  await page.getByRole("option").filter({ hasText: "Другой агент" }).click();
  const guard = page.getByRole("dialog", { name: "Несохранённые изменения" });
  await expect(guard).toBeVisible();
  await guard.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Черновик названия");
  await page.getByTestId("agent-picker-trigger").click();
  await page.getByRole("option").filter({ hasText: "Другой агент" }).click();
  await guard.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/${other.id}/overview$`));
  for (const [alias, target] of [["prompting", "instructions"], ["models", "advanced"], ["settings", "profile"], ["functions", "actions"], ["messages", "test"]]) {
    await page.goto(`/app/ai-agents/${other.id}/${alias}`);
    await expect(page).toHaveURL(new RegExp(`/${other.id}/${target}$`));
    await expect(page.getByTestId("ai-agent-editor")).toBeVisible();
  }
});

test("knowledge has full reading and independent saving while configuration is dirty", async ({ page }) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Материалы агента", status: "draft" });
  const content = "Полное содержание.\n".repeat(24) + "Последняя строка материала.";
  const item = await session.create<BusinessKnowledgeItem>("ai/knowledge-items", { bot: bot.id, title: "Длинный материал", content, category: "policy", is_active: true, customer_visible: false });
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await page.getByRole("textbox", { name: "Название", exact: true }).fill("Несохранённое название");
  await openSection(page, "Знания");
  await page.getByRole("button", { name: "Длинный материал", exact: true }).click();
  const reading = page.getByRole("dialog", { name: "Длинный материал", exact: true });
  await expect(reading.getByText(content, { exact: true })).toBeVisible();
  await expect(reading.getByRole("textbox")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(reading).toBeHidden();
  await expect(page.getByRole("button", { name: "Длинный материал", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Настроить", exact: true }).click();
  const editing = page.getByRole("dialog");
  await editing.getByRole("textbox", { name: /^Содержание/ }).fill("Обновлённый материал");
  await editing.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(editing).toBeHidden();
  expect((await session.read(`ai/knowledge-items/${item.id}`)).content).toBe("Обновлённый материал");
  expect((await session.read(`bots/${bot.id}`)).name).toBe("Материалы агента");
  await openSection(page, "Профиль");
  await expect(page.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Несохранённое название");
  await page.getByTestId("agent-save-bar").getByRole("button", { name: "Отмена", exact: true }).click();
});

test("keyboard focus keeps the instruction above fixed navigation and the dirty save bar", async ({ page }) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Keyboard focus", status: "draft" });
  await page.goto(`/app/ai-agents/${bot.id}/instructions`);
  await page.getByRole("textbox", { name: "Описание роли", exact: true }).fill("Unsaved role");
  await page.keyboard.press("Tab");
  const instruction = page.getByRole("textbox", { name: "Главная инструкция", exact: true });
  await expect(instruction).toBeFocused();
  const field = (await instruction.boundingBox())!;
  const footer = (await page.getByTestId("agent-save-bar").boundingBox())!;
  const header = (await page.getByRole("banner").boundingBox())!;
  expect(field.y).toBeGreaterThanOrEqual(header.y + header.height);
  expect(field.y + 30).toBeLessThan(footer.y);
});

test("test chat overlays the editor below the global header and retains retry/history", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Тестовый чат", status: "draft" });
  await session.create("ai/agent-profiles", { bot: bot.id, name: bot.name, is_active: true, system_prompt: "Use saved business facts" });
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByRole("button", { name: "Открыть сообщения", exact: true })).toHaveCount(0);
  const trigger = editor.getByRole("button", { name: "Тестовый чат", exact: true });
  await trigger.scrollIntoViewIfNeeded();
  const name = editor.getByRole("textbox", { name: "Название", exact: true });
  const before = await name.boundingBox();
  const beforeScroll = await page.evaluate(() => window.scrollY);
  await trigger.focus();
  await page.keyboard.press("Enter");
  const panel = page.getByTestId("agent-preview-panel");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("button", { name: "Закрыть", exact: true })).toBeFocused();
  const header = (await page.locator("[data-app-header]").boundingBox())!;
  const box = (await panel.boundingBox())!;
  const viewport = page.viewportSize()!;
  expect(box.y).toBeCloseTo(header.y + header.height, 0);
  expect(box.y + box.height).toBeCloseTo(viewport.height, 0);
  expect(box.x + box.width).toBeCloseTo(viewport.width, 0);
  expect(box.width).toBeCloseTo(viewport.width < 640 ? viewport.width : Math.max(360, viewport.width / 3), 0);
  expect(await name.boundingBox()).toEqual(before);
  expect(await page.evaluate(() => window.scrollY)).toBe(beforeScroll);
  expect(await page.evaluate(() => Boolean(document.elementFromPoint(innerWidth - 40, 20)?.closest("[data-app-header]")))).toBe(true);
  const message = panel.getByRole("textbox");
  const url = `**/api/bots/${bot.id}/preview/`;
  await message.fill("Проверочный вопрос");
  await page.route(url, route => route.fulfill({ status: 503, json: { detail: "Synthetic preview failure" } }));
  await panel.getByRole("button", { name: "Проверить ответ", exact: true }).click();
  await expect(panel.getByRole("alert").first()).toBeVisible();
  await expect(message).toHaveValue("Проверочный вопрос");
  await page.unroute(url);
  await page.route(url, route => route.fulfill({ json: { reply: "Проверочный ответ", summary: "Тестовый результат", handoff_required: false, automatic_reply_enabled: false, provider_state: "mock", sources: [] } }));
  await panel.getByRole("button", { name: "Проверить ответ", exact: true }).click();
  await expect(panel.getByRole("log")).toContainText("Проверочный ответ");
  await expect(message).toHaveValue("");
  await message.fill("Следующий вопрос");
  await page.keyboard.press("Escape");
  await expect(panel).toBeHidden();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(message).toHaveValue("Следующий вопрос");
  await expect(panel.getByRole("log")).toContainText("Проверочный ответ");
  await page.screenshot({ path: info.outputPath("test-chat-overlay.png") });
  await panel.getByRole("button", { name: "Новый тест", exact: true }).click();
  await expect(panel.getByRole("log")).toHaveText("");
  await panel.getByRole("button", { name: "Закрыть", exact: true }).click();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByTestId("header-account-link").focus();
  await expect(panel).toBeHidden();
  await expect(page.getByTestId("header-account-link")).toBeFocused();
});

test("agent picker paints above the advanced editor fields", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await createAgent(page, session, { name: "Меню агента", status: "draft" });
  await page.goto(`/app/ai-agents/${bot.id}/advanced`);
  await page.getByTestId("agent-picker-trigger").click();
  const panel = page.getByTestId("agent-picker-panel");
  await expect(panel).toBeVisible();
  const exposed = await panel.evaluate(element => {
    const box = element.getBoundingClientRect();
    return [0.2, 0.5, 0.8].every(y => [0.2, 0.6, 0.9].every(x =>
      element.contains(document.elementFromPoint(box.x + box.width * x, box.y + box.height * y))));
  });
  expect(exposed).toBe(true);
  await page.screenshot({ path: info.outputPath("agent-picker-layer.png") });
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("agent-picker-trigger")).toBeFocused();
});
