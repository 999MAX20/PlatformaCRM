import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Bot, BusinessKnowledgeItem } from "../src/types";

async function fixture(page: Page) {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Knowledge acceptance", scenario: "inbox", status: "draft" });
  return { session, bot, path: `/app/ai-agents/${bot.id}/knowledge` };
}

test("topic shortcuts remain after create; edit persists and eligibility follows both flags", async ({ page }) => {
  const { session, bot, path } = await fixture(page);
  await page.goto(path);
  await page.getByRole("button", { name: "Цены и услуги Продажи", exact: true }).click();
  const editor = page.getByRole("dialog", { name: "Новое знание", exact: true });
  await expect(editor.getByRole("textbox", { name: /^Содержание/ })).toHaveValue("");
  await editor.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: /^Содержание/ })).toHaveAttribute("aria-invalid", "true");
  await editor.getByRole("textbox", { name: /^Содержание/ }).fill("Консультация стоит 5000 тенге.");
  await editor.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(editor).toBeHidden();
  for (const name of ["Цены и услуги Продажи", "График и адрес Бизнес", "Правила записи Правила", "Частые вопросы Частые вопросы"]) {
    await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
  }
  let rows = (await session.read("ai/knowledge-items", { agent: bot.id })).results as BusinessKnowledgeItem[];
  expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({ bot: bot.id, customer_visible: false, is_active: true });
  await expect(page.getByText("Не разрешено для ответов клиентам", { exact: true })).toBeVisible();
  await expect(page.getByText("В контексте", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Редактировать", exact: true }).click();
  const editing = page.getByRole("dialog", { name: "Редактировать знание", exact: true });
  await editing.getByRole("textbox", { name: /^Содержание/ }).fill("Консультация стоит 6000 тенге.");
  await editing.getByRole("checkbox", { name: /^Разрешаю использовать/ }).check();
  await editing.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(editing).toBeHidden();
  await page.reload();
  await expect(page.getByText("Доступно агенту", { exact: true })).toBeVisible();
  rows = (await session.read("ai/knowledge-items", { agent: bot.id })).results;
  expect(rows).toHaveLength(1);
  expect(rows[0].content).toBe("Консультация стоит 6000 тенге.");
  await page.getByRole("button", { name: "Редактировать", exact: true }).click();
  await editing.getByRole("checkbox", { name: "Материал включён", exact: true }).uncheck();
  await editing.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(editing).toBeHidden();
  await expect(page.getByText("Выключено", { exact: true })).toBeVisible();
});

test("knowledge draft survives Escape, backdrop, close and browser back; discard is explicit", async ({ page }) => {
  const { session, bot, path } = await fixture(page);
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await page.goto(path);
  await page.getByRole("button", { name: "Добавить знание", exact: true }).click();
  const editor = page.getByRole("dialog", { name: "Новое знание", exact: true });
  await editor.getByRole("textbox", { name: /^Название/ }).fill("Черновик");
  await editor.getByRole("textbox", { name: /^Содержание/ }).fill("Несохранённый текст");
  const guard = page.getByRole("dialog", { name: "Несохранённый материал", exact: true });
  await page.keyboard.press("Escape");
  await expect(guard).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(guard).toBeHidden();
  await expect(editor.getByRole("textbox", { name: /^Содержание/ })).toHaveValue("Несохранённый текст");
  await editor.getByRole("button", { name: "Закрыть", exact: true }).click();
  await guard.getByRole("button", { name: "Продолжить редактирование", exact: true }).click();
  await page.locator(".platforma-overlay-backdrop").click({ position: { x: 2, y: 2 } });
  await expect(guard).toBeVisible();
  await guard.getByRole("button", { name: "Продолжить редактирование", exact: true }).click();
  await page.goBack();
  await expect(guard).toBeVisible();
  await guard.getByRole("button", { name: "Продолжить редактирование", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/${bot.id}/knowledge$`));
  await expect(editor.getByRole("textbox", { name: /^Содержание/ })).toHaveValue("Несохранённый текст");
  const blocked = await page.evaluate(() => {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  });
  expect(blocked).toBe(true);
  await editor.getByRole("button", { name: "Отмена", exact: true }).click();
  await guard.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await expect(editor).toBeHidden();
  expect((await session.read("ai/knowledge-items", { agent: bot.id })).results).toHaveLength(0);
  await expect(page.getByRole("button", { name: "Добавить знание", exact: true })).toBeFocused();
});

test("shared library exposes full text and material-wide permission; connect and disconnect preserve original", async ({ page }) => {
  const { session, bot, path } = await fixture(page);
  const content = "Общие условия бизнеса.\n".repeat(40) + "Последняя важная строка.";
  const item = await session.create<BusinessKnowledgeItem>("ai/knowledge-items", { title: "Общий материал для проверки", content, category: "policy", is_active: true, customer_visible: false });
  await page.goto(path);
  await page.getByRole("button", { name: "Из библиотеки бизнеса", exact: true }).click();
  const library = page.getByRole("dialog", { name: "Из библиотеки бизнеса", exact: true });
  const article = library.locator("article").filter({ hasText: item.title });
  await expect(library.getByText(/без создания копии/)).toBeVisible();
  await expect(article.getByText(/все клиентские агенты/)).toBeVisible();
  await expect(article.getByRole("button", { name: "Подключить", exact: true })).toBeDisabled();
  await article.getByRole("button", { name: "Читать полностью", exact: true }).click();
  await expect(article.getByRole("button", { name: "Свернуть текст", exact: true })).toHaveAttribute("aria-expanded", "true");
  expect(await article.locator("p").filter({ hasText: "Последняя важная строка." }).evaluate(el => el.scrollHeight <= el.clientHeight + 1)).toBe(true);
  await article.getByRole("checkbox").check();
  await article.getByRole("button", { name: "Подключить", exact: true }).click();
  await expect(article).toHaveCount(0);
  await library.getByRole("button", { name: "Закрыть", exact: true }).click();
  await expect(page.getByRole("button", { name: item.title, exact: true })).toBeVisible();
  expect((await session.read(`ai/knowledge-items/${item.id}`)).customer_visible).toBe(true);
  await page.reload();
  await page.getByRole("button", { name: "Отключить", exact: true }).click();
  await expect(page.getByRole("button", { name: item.title, exact: true })).toHaveCount(0);
  expect((await session.read(`ai/knowledge-items/${item.id}`)).content).toBe(content);
  expect((await session.read("ai/knowledge-items", { agent: bot.id })).results).toHaveLength(0);
});

test("agent dialogs dim without blur, including nested discard and create; other pages retain their default", async ({ page }) => {
  const { bot, path } = await fixture(page);
  await page.goto(path);
  await page.getByRole("button", { name: "Добавить знание", exact: true }).click();
  const editor = page.getByRole("dialog", { name: "Новое знание", exact: true });
  await expect(editor).toBeVisible();
  expect(await page.locator(".platforma-overlay-backdrop").evaluate(el => getComputedStyle(el).backdropFilter)).toBe("none");
  await editor.getByRole("textbox", { name: /^Название/ }).fill("Черновик");
  await page.keyboard.press("Escape");
  for (const backdrop of await page.locator(".platforma-overlay-backdrop").all()) expect(await backdrop.evaluate(el => getComputedStyle(el).backdropFilter)).toBe("none");
  await page.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await page.getByRole("button", { name: "Создать агента", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await page.locator(".platforma-overlay-backdrop").evaluate(el => getComputedStyle(el).backdropFilter)).toBe("none");
  await page.keyboard.press("Escape");
  await page.goto(`/app/ai-agents/${bot.id}/knowledge`);
});
