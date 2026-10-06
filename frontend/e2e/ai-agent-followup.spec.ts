import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Bot } from "../src/types";

test.beforeEach(({ page }) => {
  page.setDefaultTimeout(15_000);
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated fixtures");
  test.setTimeout(180_000);
});

test("deleting legacy inbox agents updates the list without a false error", async ({ page }) => {
  const session = await crmSession(page);
  const first = await session.create<Bot>("bots", { name: "Legacy one" });
  const second = await session.create<Bot>("bots", { name: "Legacy two" });
  await page.goto(`/app/ai-agents/${first.id}/profile`);
  for (const bot of [first, second]) {
    const editor = page.getByTestId("ai-agent-editor");
    await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue(bot.name);
    await editor.getByRole("button", { name: "Удалить агента", exact: true }).click();
    const removed = page.waitForResponse(r => r.request().method() === "DELETE" && r.url().endsWith(`/api/bots/${bot.id}/`));
    await page.getByRole("dialog").getByRole("button", { name: "Удалить агента", exact: true }).click();
    expect((await removed).status()).toBe(204);
    await expect(page.getByTestId("agent-navigation").getByText(bot.name, { exact: true })).toHaveCount(0);
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page).not.toHaveURL(new RegExp(`/ai-agents/${bot.id}/`));
  }
});

test("help opens only from icon; mouse-selected CRM survives reload; deletion confirms and recovers", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.goto("/app/ai-agents");
  await page.getByTestId("agent-navigation").getByRole("button", { name: "Создать агента", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Новый агент" });
  await dialog.getByRole("textbox").fill("CRM follow-up");
  const card = dialog.getByText("CRM и аналитика", { exact: true });
  await card.hover();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  const help = dialog.getByRole("button", { name: "Подробнее: CRM и аналитика", exact: true });
  if (info.project.name === "mobile-chromium") await help.tap();
  else await help.hover();
  const hint = page.getByRole("tooltip");
  await expect(hint).toBeVisible();
  const box = await dialog.boundingBox();
  const tip = await hint.boundingBox();
  if (info.project.name === "desktop-chromium") expect(tip!.x).toBeGreaterThan(box!.x + box!.width);
  else {
    const label = await card.boundingBox();
    expect(tip!.y).toBeGreaterThan(label!.y + label!.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
  }
  await page.screenshot({ path: info.outputPath("scenario-help.png"), fullPage: true });
  await dialog.getByRole("textbox").click();
  await expect(hint).toHaveCount(0);
  await card.click();
  await expect(dialog.getByRole("radio", { name: /^CRM и аналитика/ })).toBeChecked();
  const posted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/bots/"));
  await dialog.getByRole("button", { name: "Создать агента", exact: true }).click();
  const response = await posted;
  expect(response.status()).toBe(201);
  const bot: Bot = await response.json();
  expect(bot.scenario).toBe("crm");
  expect((await session.read(`bots/${bot.id}`)).settings_json.scenario).toBe("crm");
  await expect(page).toHaveURL(new RegExp(`/ai-agents/${bot.id}/profile$`));
  await page.reload();
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByRole("tab", { name: "Работа с CRM", exact: true })).toBeVisible();
  await expect(editor.getByRole("tab", { name: "Каналы", exact: true })).toHaveCount(0);
  await editor.getByRole("textbox", { name: "Название", exact: true }).fill("Unsaved rename");
  const remove = editor.getByRole("button", { name: "Удалить агента", exact: true });
  await remove.click();
  const confirmation = page.getByRole("dialog", { name: "Удалить агента «CRM follow-up»?" });
  await expect(confirmation.getByText(/Переписка, история действий/)).toBeVisible();
  await confirmation.getByRole("button", { name: "Отмена", exact: true }).click();
  expect((await session.read(`bots/${bot.id}`)).scenario).toBe("crm");
  await page.route(`**/api/bots/${bot.id}/`, route => route.request().method() === "DELETE"
    ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary delete failure" }) })
    : route.continue());
  await remove.click();
  await confirmation.getByRole("button", { name: "Удалить агента", exact: true }).click();
  await expect(editor.getByRole("alert").first()).toBeVisible();
  await expect(editor.getByRole("textbox", { name: "Название", exact: true })).toHaveValue("Unsaved rename");
  await page.unroute(`**/api/bots/${bot.id}/`);
  await remove.click();
  await page.screenshot({ path: info.outputPath("delete-confirmation.png"), fullPage: true });
  const removed = page.waitForResponse(response => response.request().method() === "DELETE" && response.url().endsWith(`/api/bots/${bot.id}/`));
  await confirmation.getByRole("button", { name: "Удалить агента", exact: true }).click();
  expect((await removed).status()).toBe(204);
  await expect.poll(() => session.list<Bot>("bots").then(bots => bots.some(item => item.id === bot.id))).toBe(false);
  await expect(page).not.toHaveURL(new RegExp(`/ai-agents/${bot.id}/`));
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const replacement = await session.create<Bot>("bots", { name: "Replacement CRM", scenario: "crm" });
  expect(replacement.scenario).toBe("crm");
});

test("keyboard help and deletion cancellation remain usable in RU KK EN", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<Bot>("bots", { name: "Keep history", scenario: "inbox" });
  for (const [locale, removeLabel, createLabel, helpLabel] of [
    ["ru", "Удалить агента", "Создать агента", "Подробнее: Общение с клиентами"],
    ["kk", "Агентті жою", "Агент жасау", "Толығырақ: Клиенттермен байланыс"],
    ["en", "Delete agent", "Create agent", "More about Customer conversations"],
  ]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/ai-agents/${bot.id}/profile`);
    const remove = page.getByTestId("ai-agent-editor").getByRole("button", { name: removeLabel, exact: true });
    await remove.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: info.outputPath(`delete-${locale}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect((await session.read(`bots/${bot.id}`)).id).toBe(bot.id);
    await page.getByTestId("agent-navigation").getByRole("button", { name: createLabel, exact: true }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: helpLabel, exact: true }).focus();
    await expect(page.getByRole("tooltip")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("tooltip")).toHaveCount(0);
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  }
});
