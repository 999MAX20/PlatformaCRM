import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import type { AgentProfile, Bot } from "../src/types";

test.beforeEach(({}, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated API fixtures");
  test.skip(testInfo.project.name === "tablet-chromium", "Picker interaction matrix covers desktop/mobile; layout includes tablet");
  test.setTimeout(120_000);
});

async function createAgent(session: Awaited<ReturnType<typeof crmSession>>, name: string, role: string) {
  const bot = await session.create<Bot>("bots", { name, status: "draft" });
  await session.create<AgentProfile>("ai/agent-profiles", {
    bot: bot.id, name, role_description: role, tone: "friendly", language: "ru", is_active: true,
    system_prompt: "Используйте сведения компании.", rules_json: [], allowed_tools_json: { tools: ["handoff_to_manager"] }, escalation_rules_json: [],
  });
  return bot;
}

test("agent navigation searches, creates and protects drafts in the expanded sidebar or compact picker", async ({ page }, testInfo) => {
  const expanded = testInfo.project.name === "desktop-chromium";
  if (expanded) await page.setViewportSize({ width: 1600, height: 900 });
  const session = await crmSession(page);
  const first = await createAgent(session, "Администратор клиники", "Отвечает на вопросы клиентов");
  const secondName = "Әкімші — запись и подтверждение приёма — clinic appointments and customer support — длинное название агента";
  const second = await createAgent(session, secondName, "Подтверждение записи");
  await page.goto(`/app/ai-agents/${first.id}/profile`);
  const picker = page.getByTestId("agent-picker-trigger");
  const popover = page.getByTestId("agent-picker-panel");
  const navigation = page.getByTestId("agent-navigation");
  const editor = page.getByTestId("ai-agent-editor");
  const originalWidth = (await navigation.boundingBox())!.width;
  const create = navigation.getByRole("button", { name: "Создать агента", exact: true });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: testInfo.outputPath("navigation-profile.png") });
  await create.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(create).toBeFocused();
  async function openList() {
    await page.evaluate(() => window.scrollTo(0, 0));
    if (expanded) await popover.getByRole("combobox").focus();
    else {
      await picker.focus();
      await page.keyboard.press("ArrowDown");
    }
  }
  await openList();
  const search = popover.getByRole("combobox");
  await expect(search).toBeFocused();
  await search.fill("нет такого назначения");
  await expect(popover.getByText("Ничего не найдено", { exact: true })).toBeVisible();
  await search.fill("подтверждение записи");
  await expect(popover.getByRole("option")).toHaveCount(1);
  await expect(popover.getByRole("option")).toContainText(secondName);
  if (expanded) await search.fill("");
  else {
    await page.keyboard.press("Escape");
    await expect(popover).toBeHidden();
    await expect(picker).toBeFocused();
  }

  await editor.getByRole("textbox", { name: "Название", exact: true }).fill("Несохранённое имя");
  await expect(create).toBeDisabled();
  await openList();
  await search.fill("подтверждение записи");
  await page.keyboard.press("Enter");
  const guard = page.getByRole("dialog", { name: "Несохранённые изменения", exact: true });
  await expect(guard).toBeVisible();
  await expect(editor.getByRole("heading", { name: first.name, exact: true })).toBeVisible();
  await guard.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Несохранённое имя");
  await openList();
  await search.fill("подтверждение записи");
  await page.keyboard.press("Enter");
  await guard.getByRole("button", { name: "Сохранить и продолжить", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/app/ai-agents/${second.id}/profile$`));
  expect((await session.read(`bots/${first.id}`)).name).toBe("Несохранённое имя");
  const label = expanded ? popover.getByRole("option", { selected: true }).locator("p").first() : picker.locator("span");
  await expect(expanded ? popover.getByRole("option", { selected: true }) : picker).toHaveAttribute("title", secondName);
  expect((await navigation.boundingBox())!.width).toBe(originalWidth);
  const truncation = await label.evaluate(element => ({ visible: element.clientWidth, text: element.scrollWidth }));
  expect(truncation.text).toBeGreaterThan(truncation.visible);
  await openList();
  await expect(popover.getByRole("option", { selected: true })).toContainText(secondName);
  await page.screenshot({ path: testInfo.outputPath("selected-long-name.png") });
  expect((await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze()).violations).toEqual([]);
  if (!expanded) await page.keyboard.press("Escape");

  await editor.getByRole("textbox", { name: "Название", exact: true }).fill("Отменить это имя");
  await editor.getByRole("tab", { name: "Действия", exact: true }).click();
  await editor.getByRole("tab", { name: "Профиль", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Отменить это имя");
  await editor.locator("footer").getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue(secondName);
  await editor.getByRole("textbox", { name: "Название", exact: true }).fill("Не сохранять это имя");
  await openList();
  await search.fill("Несохранённое имя");
  await page.keyboard.press("Enter");
  await guard.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/app/ai-agents/${first.id}/profile$`));
  expect((await session.read(`bots/${second.id}`)).name).toBe(secondName);
});

test("picker presents a scrollable long list and recoverable loading, error and empty states", async ({ page }, testInfo) => {
  const session = await crmSession(page);
  const bots = await session.list<Bot>("bots");
  const seed = bots[0];
  const names = ["Очень длинное имя администратора клиники и поддержки клиентов", "Әкімші — қабылдауға жазылу және клиенттердің сұрақтарына жауап беру", "Clinic appointments and customer support administrator"];
  const rows = Array.from({ length: 35 }, (_, index) => ({ ...seed, id: 1000 + index, name: `${names[index % names.length]} ${index + 1}`, status: index % 2 ? "paused" : "draft" }));
  let state: "list" | "loading" | "error" | "empty" = "list";
  let release: (() => void) | undefined;
  await page.route(/\/api\/bots\/(?:\?.*)?$/, async route => {
    if (state === "loading") await new Promise<void>(resolve => { release = resolve; });
    if (state === "error") return route.fulfill({ status: 503, json: { code: "service_unavailable" } });
    return route.fulfill({ json: state === "empty" ? [] : [seed, ...rows] });
  });
  await page.goto(`/app/ai-agents/${seed.id}/profile`);
  const picker = page.getByTestId("agent-picker-trigger");
  const popover = page.getByTestId("agent-picker-panel");
  await picker.click();
  await expect(popover.getByRole("option")).toHaveCount(36);
  expect(await popover.getByRole("listbox").evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
  for (const fragment of ["Очень длинное", "Әкімші", "Clinic appointments"]) {
    await popover.getByRole("combobox").fill(fragment);
    await expect(popover.getByRole("option").first()).toContainText(fragment);
  }
  await popover.getByRole("combobox").fill("");
  for (let index = 0; index < 30; index++) await page.keyboard.press("ArrowDown");
  expect(await popover.getByRole("listbox").evaluate(element => element.scrollTop)).toBeGreaterThan(0);
  await page.screenshot({ path: testInfo.outputPath("scrolling-agents.png") });
  await page.keyboard.press("Escape");
  await expect(picker).toBeFocused();

  state = "loading";
  await page.reload({ waitUntil: "domcontentloaded" });
  await picker.click();
  await expect(popover.getByText("Загружаем агентов...", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("picker-loading.png") });
  state = "error";
  await expect.poll(() => Boolean(release)).toBe(true);
  release!();
  await expect(popover.getByRole("button", { name: "Повторить", exact: true })).toBeVisible({ timeout: 20_000 });
  await page.screenshot({ path: testInfo.outputPath("picker-error.png") });
  state = "list";
  await popover.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(popover.getByRole("option")).toHaveCount(36);
  state = "empty";
  await page.reload();
  await picker.click();
  await expect(picker).toContainText("Все агенты");
  await expect(popover.getByText("Создайте первого агента", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("picker-empty.png") });
});

test("knowledge and channel dialogs remain usable; failed save preserves the draft", async ({ page }, testInfo) => {
  const session = await crmSession(page);
  const bot = await createAgent(session, "Проверка настроек", "Тестовая роль в изолированной базе");
  await page.goto(`/app/ai-agents/${bot.id}/knowledge`);
  const editor = page.getByTestId("ai-agent-editor");
  await editor.getByRole("button", { name: "Добавить знание", exact: true }).click();
  const modal = page.getByRole("dialog");
  await modal.getByRole("textbox", { name: "Название", exact: true }).fill("Правила записи");
  await modal.getByRole("textbox", { name: "Содержание", exact: true }).fill("Перенос записи через администратора.");
  await page.screenshot({ path: testInfo.outputPath("knowledge-dialog.png") });
  await modal.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(modal).toBeHidden();
  await editor.locator("article").filter({ hasText: "Правила записи" }).getByRole("button", { name: "Настроить", exact: true }).click();
  await expect(modal.getByRole("textbox", { name: "Содержание", exact: true })).toHaveValue("Перенос записи через администратора.");
  await page.keyboard.press("Escape");
  await editor.getByRole("tab", { name: "Каналы", exact: true }).click();
  for (const channel of ["website", "telegram", "whatsapp", "instagram"]) {
    const trigger = page.locator(`[data-focus-return-id="ai-agent-channel-${bot.id}-${channel}"]`);
    await trigger.click();
    await expect(modal).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`channel-${channel}.png`) });
    await page.keyboard.press("Escape");
    await expect(modal).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect((await session.read(`bots/${bot.id}`)).status).toBe("draft");
  await editor.getByRole("tab", { name: "Профиль", exact: true }).click();
  await editor.getByRole("textbox", { name: "Название", exact: true }).fill("Сохранить после ошибки");
  const writes = /\/api\/(?:bots|ai\/agent-profiles)\/\d+\/$/;
  await page.route(writes, route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { code: "service_unavailable" } }) : route.continue());
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("alert").first()).toBeVisible();
  await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Сохранить после ошибки");
  await page.unroute(writes);
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
});

test("manager cannot enter agent configuration or see agent navigation", async ({ page }) => {
  await crmSession(page, "business_manager@example.com");
  await page.goto("/app/ai-agents/1/profile");
  await expect(page.getByTestId("forbidden-state")).toBeVisible();
  await expect(page.getByTestId("ai-agent-editor")).toHaveCount(0);
  await expect(page.getByTestId("agent-navigation")).toHaveCount(0);
});
