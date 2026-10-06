import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Bot, BusinessKnowledgeItem } from "../src/types";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable API fixtures");
  test.setTimeout(120_000);
});

test("visible profile, deliberate template and navigation draft protection", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: `UX ${info.project.name}`, status: "draft" });
  await session.create("ai/agent-profiles", { bot: bot.id, name: "Legacy profile name", is_active: true, role_description: "Existing role", system_prompt: "Keep this instruction", allowed_tools_json: { tools: [] } });
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toBeVisible();
  await expect(editor.getByLabel("Название профиля", { exact: true })).toHaveCount(0);
  await editor.getByRole("button", { name: "Шаблон: администратор стоматологии", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText(/Он заменит описание роли/)).toBeVisible();
  await dialog.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Keep this instruction");
  await editor.getByRole("button", { name: "Шаблон: администратор стоматологии", exact: true }).click();
  await dialog.getByRole("button", { name: "Заполнить по шаблону" }).click();
  await expect(editor.getByRole("textbox", { name: "Описание роли", exact: true })).not.toHaveValue("Existing role");
  await editor.getByRole("button", { name: "Открыть сообщения", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Несохранённые изменения" })).toBeVisible();
  await dialog.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).not.toHaveValue("Keep this instruction");
  await editor.getByRole("button", { name: "Открыть сообщения", exact: true }).click();
  await dialog.getByRole("button", { name: "Отменить изменения", exact: true }).click();
  await expect(page).toHaveURL(/conversations$/);
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue("Keep this instruction");
  await page.screenshot({ path: info.outputPath("profile-template-guard.png"), fullPage: true });
});

test("knowledge explains requirements, rejects whitespace, retains failed save and persists retry", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Knowledge UX", status: "draft" });
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
  const bot = await session.create<Bot>("bots", { name: "Recovery", status: "draft" });
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
