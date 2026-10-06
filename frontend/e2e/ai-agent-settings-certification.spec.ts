import { expect, test, type Locator, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { AgentProfile, Bot } from "../src/types";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixture database required");
  test.setTimeout(240_000);
});

async function choose(page: Page, editor: Locator, label: string, option: string) {
  await editor.getByLabel(label, { exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

for (const scenario of ["inbox", "crm"] as const) {
  test(`${scenario}: every profile field persists, invalid name preserves saved settings, cancel restores draft`, async ({ page }, info) => {
    const session = await crmSession(page);
    const bot = await session.create<Bot>("bots", { name: `Audit ${scenario}`, scenario });
    await page.goto(`/app/ai-agents/${bot.id}/profile`);
    const editor = page.getByTestId("ai-agent-editor");
    await editor.getByRole("textbox", { name: "Название", exact: true }).fill(`Saved ${scenario}`);
    await choose(page, editor, "Язык", "English");
    await choose(page, editor, "Тон", "Формальный");
    await choose(page, editor, "Режим ответов", "Экономный режим");
    for (const [label, value] of [["Описание роли", "AUDIT_ROLE: business receptionist"], ["Главная инструкция", "AUDIT_INSTRUCTION: explain only supplied business facts"], ["Правила", "AUDIT_RULE_ONE\nAUDIT_RULE_TWO"]]) {
      await editor.getByRole("textbox", { name: label, exact: true }).fill(value);
    }
    const freedom = editor.getByRole("slider");
    await freedom.focus();
    await freedom.press("Home");
    await freedom.press("ArrowRight");
    await freedom.press("ArrowRight");
    await editor.getByRole("switch", { name: "Память диалогов", exact: true }).uncheck();
    const save = editor.getByRole("button", { name: "Сохранить изменения", exact: true });
    await save.click();
    await expect(save).toBeDisabled();
    let saved = await session.read(`bots/${bot.id}`);
    let profile = (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)!;
    expect(saved).toMatchObject({ name: `Saved ${scenario}`, default_language: "en", settings_json: { model: "gpt-4o-mini", temperature: 0.2, memory_enabled: false } });
    expect(profile).toMatchObject({ language: "en", tone: "formal", role_description: "AUDIT_ROLE: business receptionist", system_prompt: "AUDIT_INSTRUCTION: explain only supplied business facts", rules_json: { items: ["AUDIT_RULE_ONE", "AUDIT_RULE_TWO"] } });
    await page.reload();
    await expect(editor.getByRole("textbox", { name: "Описание роли", exact: true })).toHaveValue(profile.role_description);
    await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue(profile.system_prompt);
    await expect(editor.getByRole("textbox", { name: "Правила", exact: true })).toHaveValue("AUDIT_RULE_ONE\nAUDIT_RULE_TWO");
    await expect(editor.getByRole("slider")).toHaveValue("0.2");
    await expect(editor.getByRole("switch", { name: "Память диалогов", exact: true })).not.toBeChecked();
    await editor.getByRole("textbox", { name: "Название", exact: true }).fill("   ");
    await editor.getByRole("textbox", { name: "Главная инструкция", exact: true }).fill("UNSAVED_INSTRUCTION");
    await expect(save).toBeDisabled();
    saved = await session.read(`bots/${bot.id}`);
    profile = (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)!;
    expect(saved.name).toBe(`Saved ${scenario}`);
    expect(profile.system_prompt).not.toContain("UNSAVED");
    await editor.getByRole("button", { name: "Отмена", exact: true }).click();
    await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue(`Saved ${scenario}`);
    await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue(profile.system_prompt);
    await page.screenshot({ path: info.outputPath(`${scenario}-profile.png`), fullPage: true });
    if (scenario === "crm") {
      await editor.getByRole("tab", { name: "Знания", exact: true }).click();
      const sourceNames = ["Клиенты", "Заявки", "Сделки", "Задачи", "Календарь", "База знаний"];
      for (const name of sourceNames) await editor.getByRole("checkbox", { name, exact: true }).uncheck();
      await save.click();
      await expect(save).toBeDisabled();
      expect((await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)?.rules_json.sources).toEqual([]);
      for (const name of sourceNames) await editor.getByRole("checkbox", { name, exact: true }).check();
      await save.click();
      await expect(save).toBeDisabled();
      await editor.getByRole("tab", { name: "Действия", exact: true }).click();
      for (const capability of await editor.getByRole("checkbox").all()) await capability.check();
      const analytics = editor.getByRole("switch", { name: "Разрешить аналитику", exact: true });
      await analytics.click();
      await save.click();
      await expect(save).toBeDisabled();
      profile = (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)!;
      expect(profile.rules_json.sources).toEqual(expect.arrayContaining(["clients", "leads", "deals", "tasks", "appointments", "knowledge"]));
      expect(profile.allowed_tools_json.tools).toEqual(expect.arrayContaining(["crm_read", "crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"]));
      await page.reload();
      for (const capability of await editor.getByRole("checkbox").all()) await expect(capability).toBeChecked();
      await expect(analytics).toHaveAttribute("aria-checked", "false");
      expect(profile.rules_json.analyst_enabled).toBe(false);
      await session.action(`bots/${bot.id}/activate`);
      const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
      const denied = await page.request.get(`${api}/api/ai/analyst/history/`, { headers: session.headers, params: { business: session.business, agent: bot.id, start: "2026-10-01", end: "2026-10-06" } });
      expect(denied.status()).toBe(403);
      await analytics.click();
      await save.click();
      await expect(save).toBeDisabled();
      await expect(editor.getByRole("tab", { name: "Аналитика", exact: true })).toBeVisible();
    }
  });
}

test("customer action thresholds, capabilities and handoff rules persist through tabs and reload", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Audit action controls" });
  await session.create("ai/agent-profiles", { bot: bot.id, name: bot.name, allowed_tools_json: { tools: ["handoff_to_manager"] } });
  await page.goto(`/app/ai-agents/${bot.id}/actions`);
  const editor = page.getByTestId("ai-agent-editor");
  await choose(page, editor, "Что делать после диалога", "Заявки, задачи и черновики сделок");
  await choose(page, editor, "Создание новых записей", "Автоматически по разрешению бизнеса");
  for (const name of ["Работать с записью в календарь", "Автоматически отправлять ответ"]) {
    const control = editor.getByRole("switch", { name, exact: true });
    if (await control.getAttribute("aria-checked") === "false") await control.click();
  }
  await editor.getByRole("switch", { name: "Проверять неуверенные решения", exact: true }).click();
  await editor.getByRole("button", { name: "Расширенные ограничения", exact: true }).click();
  await editor.getByRole("spinbutton", { name: "Максимальная длина автоответа", exact: true }).fill("320");
  for (const slider of await editor.getByRole("slider").all()) { await slider.focus(); await slider.press("End"); }
  for (const control of await editor.getByRole("switch").all()) {
    if (await control.isEnabled() && await control.getAttribute("aria-checked") === "false" && !((await control.getAttribute("aria-label")) || "").startsWith("Изменить статус")) await control.click();
  }
  await editor.getByRole("textbox", { name: "Когда передавать администратору", exact: true }).fill("AUDIT_ESCALATION: complaint\nAUDIT_ESCALATION: uncertainty");
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  const saved = await session.read(`bots/${bot.id}`);
  expect(saved.settings_json.auto_crm_pipeline).toMatchObject({ enabled: true, mode: "draft_deal", creation_policy: "automatic", create_appointment: true, auto_send_reply: true, require_review_on_fallback: true, max_auto_reply_chars: 320, min_lead_confidence: 1, min_deal_confidence: 1 });
  const profile = (await session.list<AgentProfile>("ai/agent-profiles")).find(item => item.bot === bot.id)!;
  expect(profile.allowed_tools_json.tools).toEqual(expect.arrayContaining(["create_client", "create_appointment", "create_lead", "create_task", "create_deal", "handoff_to_manager"]));
  expect(profile.escalation_rules_json.items).toEqual(["AUDIT_ESCALATION: complaint", "AUDIT_ESCALATION: uncertainty"]);
  await page.reload();
  await expect(editor.getByRole("textbox", { name: "Когда передавать администратору", exact: true })).toHaveValue("AUDIT_ESCALATION: complaint\nAUDIT_ESCALATION: uncertainty");
  await editor.getByRole("button", { name: "Расширенные ограничения", exact: true }).click();
  await expect(editor.getByRole("spinbutton", { name: "Максимальная длина автоответа", exact: true })).toHaveValue("320");
  await choose(page, editor, "Что делать после диалога", "Выключено");
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  expect((await session.read(`bots/${bot.id}`)).settings_json.auto_crm_pipeline.enabled).toBe(false);
  await expect(editor.getByRole("switch", { name: "Автоматически отправлять ответ", exact: true })).toBeDisabled();
  await page.screenshot({ path: info.outputPath("customer-action-controls.png"), fullPage: true });
});

test("channel forms save synthetic settings, mask keys and expose portable website code", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Audit channel forms" });
  await page.goto(`/app/ai-agents/${bot.id}/channels`);
  const editor = page.getByTestId("ai-agent-editor");
  const card = (title: string) => editor.locator("article").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await card("Сайт").getByRole("button", { name: "Подключить", exact: true }).click();
  const dialog = page.getByRole("dialog");
  const snippet = await dialog.locator("pre").innerText();
  const scriptUrl = /src="([^"]+)"/.exec(snippet)?.[1];
  expect(scriptUrl).toBe(`${new URL(page.url()).origin}/widget/platformacrm-widget.js`);
  expect(new URL(scriptUrl!, "https://merchant.example.invalid").origin).toBe(new URL(page.url()).origin);
  await dialog.getByRole("button", { name: "Закрыть", exact: true }).click();
  await card("Сайт").getByRole("switch").click();
  await expect.poll(async () => (await session.list<{ bot: number; channel: string; status: string }>("bot-channels")).find(item => item.bot === bot.id && item.channel === "website")?.status).toBe("active");
  await card("Сайт").getByRole("switch").click();
  await expect.poll(async () => (await session.list<{ bot: number; channel: string; status: string }>("bot-channels")).find(item => item.bot === bot.id && item.channel === "website")?.status).toBe("paused");
  await card("Сайт").getByRole("switch").click();
  await expect.poll(async () => (await session.list<{ bot: number; channel: string; status: string }>("bot-channels")).find(item => item.bot === bot.id && item.channel === "website")?.status).toBe("active");
  await card("Telegram").getByRole("button", { name: "Подключить", exact: true }).click();
  await dialog.getByLabel("Ключ бота", { exact: true }).fill("short");
  await expect(dialog.getByRole("button", { name: "Сохранить ключ", exact: true })).toHaveCount(0);
  await dialog.getByLabel("Ключ бота", { exact: true }).fill("00000000:synthetic-audit-token");
  await dialog.getByRole("button", { name: "Сохранить ключ", exact: true }).click();
  await expect(dialog.getByText("Ключ сохранён приватно. Вставьте новый только для замены.", { exact: true })).toBeVisible();
  await expect(dialog.getByLabel("Ключ бота", { exact: true })).toHaveValue("");
  await expect(dialog.getByRole("link", { name: "Открыть сообщения", exact: true })).toHaveAttribute("href", "/app/conversations?channel=telegram");
  await dialog.getByRole("button", { name: "Закрыть", exact: true }).click();
  for (const provider of ["WhatsApp", "Instagram"]) {
    await card(provider).getByRole("button", { name: "Подключить", exact: true }).click();
    await dialog.getByRole("button", { name: "Нужна помощь с подключением?", exact: true }).click();
    const values = provider === "WhatsApp"
      ? [["ID номера WhatsApp", "1234567890"], ["ID бизнес-аккаунта", "998877"], ["Номер для клиентов", "+77000000000"]]
      : [["ID аккаунта Instagram", "178400000000"], ["ID страницы Facebook", "998877"], ["Instagram аккаунт", "synthetic_audit"]];
    for (const [label, value] of values) await dialog.getByLabel(label, { exact: true }).fill(value);
    const key = dialog.getByLabel("Ключ доступа", { exact: true });
    await expect(key).toHaveAttribute("type", "password");
    await key.fill("synthetic-only-audit-token");
    const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/${provider.toLowerCase()}-config/`));
    await dialog.getByRole("button", { name: /Сохранить/ }).click();
    expect((await saved).status()).toBe(200);
    await expect(key).toHaveValue("");
    await expect(dialog.getByText("Настраивается", { exact: true })).toBeVisible();
    await expect(dialog.getByText("Подключено", { exact: true })).toHaveCount(0);
    await expect(dialog.getByRole("link", { name: "Открыть сообщения", exact: true })).toHaveAttribute("href", `/app/conversations?channel=${provider.toLowerCase()}`);
    await page.screenshot({ path: info.outputPath(`${provider}-settings.png`), fullPage: true });
    await dialog.getByRole("button", { name: "Закрыть", exact: true }).click();
  }
  const stored = await session.list<{ bot: number; config_json: Record<string, unknown> }>("bot-channels");
  expect(JSON.stringify(stored.filter(item => item.bot === bot.id))).not.toContain("synthetic-only-audit-token");
});
