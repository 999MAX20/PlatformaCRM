import { openAgentSection } from "./support/agent-navigation";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import type { AgentProfile, Bot } from "../src/types";

test.beforeEach(({ page }) => {
  page.setDefaultTimeout(15_000);
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated fixtures and mock AI");
  test.setTimeout(240_000);
});

test("CRM creation is unavailable; existing CRM settings drive work, approval and analytics", async ({ page }, info) => {
  const session = await crmSession(page);
  await page.goto("/app/ai-agents");
  await page.getByTestId("agent-navigation").getByRole("button", { name: "Создать агента", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Новый агент" });
  await dialog.getByRole("textbox").fill("CRM workspace");
  const create = dialog.getByRole("button", { name: "Создать агента", exact: true });
  await expect(create).toBeDisabled();
  const inbox = dialog.getByRole("radio", { name: /^Общение с клиентами/ });
  await dialog.getByText("CRM и аналитика", { exact: true }).hover();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  await inbox.focus();
  await inbox.press("Space");
  await inbox.press("ArrowDown");
  await expect(inbox).toBeChecked();
  const crm = dialog.getByRole("radio", { name: /^CRM и аналитика/ });
  await expect(crm).toBeDisabled();
  const crmTitle = dialog.getByText("CRM и аналитика", { exact: true });
  await crmTitle.scrollIntoViewIfNeeded();
  const crmBounds = await crmTitle.boundingBox();
  await page.mouse.click(crmBounds!.x + crmBounds!.width / 2, crmBounds!.y + crmBounds!.height / 2);
  await expect(crm).not.toBeChecked();
  await expect(dialog.getByText("В разработке", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Подробнее: CRM и аналитика", exact: true }).focus();
  await expect(page.getByRole("tooltip")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  await page.screenshot({ path: info.outputPath("create-crm.png"), fullPage: true });
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  const previous = (await session.list<Bot>("bots")).find(item => item.scenario === "crm");
  if (previous) {
    const removed = await page.request.delete(`${process.env.E2E_API_BASE_URL}/api/bots/${previous.id}/`, { headers: session.headers });
    expect(removed.ok(), await removed.text()).toBeTruthy();
  }
  const bot = await session.create<Bot>("bots", { name: "CRM workspace", scenario: "crm" });
  expect(bot.scenario).toBe("crm");
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  await expect(page).toHaveURL(new RegExp(`/ai-agents/${bot.id}/profile$`));
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.locator("#agent-section-links button")).toHaveCount(7);
  await expect(editor.locator("#agent-section-links").getByRole("button", { name: "Каналы", exact: true })).toHaveCount(0);
  await expect(editor.getByRole("button", { name: "Шаблон: администратор бизнеса" })).toHaveCount(0);
  await openAgentSection(page, "Инструкции");
  await editor.getByRole("textbox", { name: "Главная инструкция", exact: true }).fill("Use only enabled sources and show the evidence.");
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  await openAgentSection(page, "Знания");
  for (const name of ["Клиенты", "Заявки", "Сделки", "Календарь"]) await editor.getByRole("checkbox", { name, exact: true }).uncheck();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  await openAgentSection(page, "Действия");
  await editor.getByRole("checkbox", { name: "Создать запись CRM", exact: true }).check();
  await editor.getByRole("button", { name: "Сохранить изменения", exact: true }).click();
  await expect(editor.getByRole("button", { name: "Сохранить изменения", exact: true })).toBeDisabled();
  const saved = (await session.list<AgentProfile>("ai/agent-profiles")).find(profile => profile.bot === bot.id)!;
  expect(saved.rules_json.sources).toEqual(["knowledge", "tasks"]);
  expect(saved.allowed_tools_json.tools).toEqual(["crm_read", "crm_create"]);
  expect(saved.system_prompt).toBe("Use only enabled sources and show the evidence.");
  await expect(editor.getByRole("switch", { name: "Изменить статус агента CRM workspace" })).toHaveCount(0);
  await session.action(`bots/${bot.id}/activate`);
  await page.reload();
  await expect.poll(async () => (await session.read(`bots/${bot.id}`)).status).toBe("active");
  await openAgentSection(page, "Работа с CRM");
  await editor.locator("summary").filter({ hasText: "Действия с CRM" }).click();
  await expect(editor.getByLabel("Раздел CRM", { exact: true })).toContainText("Задачи");
  await editor.getByRole("textbox", { name: "Сообщение агенту", exact: true }).fill("What tasks need attention?");
  const chat = page.waitForRequest(request => /\/api\/ai\/conversations\/[^/]+\/turns\/$/.test(request.url()) && request.method() === "POST");
  await editor.getByRole("button", { name: "Отправить", exact: true }).click();
  expect((await chat).postDataJSON().mode).toBe("work");
  await expect(editor.getByRole("textbox", { name: "Сообщение агенту", exact: true })).toHaveValue("");
  const title = `Confirmed ${info.project.name} ${bot.id}`;
  const proposal = await session.action("ai/tools/suggest", { business: session.business, agent: bot.id, tool_name: "crm_create", arguments: { entity: "tasks", values: { title } } });
  expect(proposal.suggested_actions[0].input_json._agent.agent_id).toBe(bot.id);
  await page.route("**/api/ai/crm/plan/", async route => {
    expect(route.request().postDataJSON().agent).toBe(bot.id);
    await route.fulfill({ json: { question: "", suggested_actions: proposal.suggested_actions } });
  });
  await editor.getByRole("textbox", { name: "Что нужно сделать?", exact: true }).fill(`Create task ${title}`);
  await editor.getByRole("button", { name: "Подготовить действие", exact: true }).click();
  const review = editor.getByRole("region", { name: "Проверка действия", exact: true });
  await review.getByRole("button", { name: "Подтвердить", exact: true }).click();
  const confirm = page.getByRole("dialog", { name: "Выполнить проверенное действие?" });
  await confirm.getByRole("button", { name: "Отмена", exact: true }).click();
  expect((await session.list<{ title: string }>("tasks")).some(task => task.title === title)).toBeFalsy();
  await review.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await confirm.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(editor.getByText("Действие выполнено", { exact: true })).toBeVisible();
  expect((await session.list<{ title: string }>("tasks")).filter(task => task.title === title)).toHaveLength(1);
  await page.screenshot({ path: info.outputPath("crm-work-confirmed.png"), fullPage: true });
  await openAgentSection(page, "Аналитика");
  await expect(editor.getByRole("heading", { name: "История и финансовый анализ", exact: true })).toBeVisible();
  await expect.poll(async () => editor.locator('[role="alert"]').count()).toBe(0);
  for (const locale of ["ru", "kk", "en"]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.reload();
    await expect(editor.locator("#agent-section-links button")).toHaveCount(7);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await editor.evaluate(async el => {
      await Promise.all(el.getAnimations({ subtree: true })
        .filter(animation => animation.effect?.getTiming().iterations !== Infinity)
        .map(animation => animation.finished.catch(() => undefined)));
    });
    const violations = (await new AxeBuilder({ page }).include('[data-testid="ai-agent-editor"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations;
    expect(violations).toEqual([]);
    await page.screenshot({ path: info.outputPath(`crm-analytics-${locale}.png`), fullPage: true });
  }
});

test("customer creation keeps its own interface and duplicate CRM choice is disabled", async ({ page }, info) => {
  const session = await crmSession(page);
  if (!(await session.list<Bot>("bots")).some(bot => bot.scenario === "crm")) await session.create("bots", { name: "CRM", scenario: "crm" });
  await page.goto("/app/ai-agents");
  await page.getByTestId("agent-navigation").getByRole("button", { name: "Создать агента", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Новый агент" });
  await expect(dialog.getByRole("radio", { name: /^CRM и аналитика/ })).toBeDisabled();
  await dialog.getByRole("textbox").fill("Customer inbox");
  await dialog.getByRole("radio", { name: /^Общение с клиентами/ }).check();
  let attempts = 0;
  let releaseFirst!: () => void;
  const firstResponse = new Promise<void>(resolve => { releaseFirst = resolve; });
  await page.route("**/api/bots/", async route => {
    if (route.request().method() !== "POST" || ++attempts > 1) return route.continue();
    await firstResponse;
    await route.fulfill({ status: 503, json: { detail: "Temporarily unavailable" } });
  });
  const submit = dialog.locator('button[type="submit"]');
  await submit.click();
  await expect(submit).toBeDisabled();
  await dialog.locator("form").evaluate(form => (form as HTMLFormElement).requestSubmit());
  expect(attempts).toBe(1);
  releaseFirst();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByRole("textbox")).toHaveValue("Customer inbox");
  await expect(dialog.locator('input[value="inbox"]')).toBeChecked();
  await expect(dialog.locator('input[value="crm"]')).toBeDisabled();
  const posted = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/bots/"));
  await submit.click();
  const created = await posted;
  expect(created.status(), await created.text()).toBe(201);
  const bot: Bot = await created.json();
  expect(bot.scenario).toBe("inbox");
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.locator("#agent-section-links").getByRole("button", { name: "Каналы", exact: true, includeHidden: true })).toHaveCount(1);
  await openAgentSection(page, "Инструкции");
  await expect(editor.locator("#agent-section-links").getByRole("button", { name: "Работа с CRM", exact: true })).toHaveCount(0);
  await expect(editor.getByRole("switch", { name: "Изменить статус агента Customer inbox" })).toHaveCount(0);
  await expect(editor.getByRole("button", { name: "Шаблон: администратор бизнеса" })).toHaveCount(0);
  await expect(editor.getByRole("textbox", { name: "Роль агента", exact: true })).toHaveValue("Администратор бизнеса");
  await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toHaveValue(/Только|Используй только данные бизнеса/);
  await page.screenshot({ path: info.outputPath("customer-profile.png"), fullPage: true });
  const cleanup = await page.request.delete(`${process.env.E2E_API_BASE_URL}/api/bots/${bot.id}/`, { headers: session.headers });
  expect(cleanup.ok(), await cleanup.text()).toBeTruthy();
});

test("creation availability banner and centered action remain usable in all locales", async ({ page }, info) => {
  await crmSession(page);
  for (const [locale, banner] of [["ru", "В разработке"], ["kk", "Әзірленуде"], ["en", "In development"]]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/ai-agents");
    const opener = page.locator('[data-focus-return-id="ai-agent-create"]');
    await opener.click();
    const dialog = page.getByRole("dialog");
    const crm = dialog.locator('input[value="crm"]');
    const inbox = dialog.locator('input[value="inbox"]');
    await expect(crm).toBeDisabled();
    await expect(dialog.getByText(banner, { exact: true })).toBeVisible();
    await dialog.getByRole("textbox").fill("Availability check");
    await inbox.check();
    await inbox.press("ArrowDown");
    await expect(inbox).toBeChecked();
    await expect(crm).not.toBeChecked();
    const submit = dialog.locator('button[type="submit"]');
    await expect(submit).toBeEnabled();
    await submit.scrollIntoViewIfNeeded();
    const bounds = await submit.boundingBox();
    const modalBounds = await dialog.boundingBox();
    expect(Math.abs(bounds!.x + bounds!.width / 2 - modalBounds!.x - modalBounds!.width / 2)).toBeLessThan(2);
    expect(await dialog.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
    expect((await new AxeBuilder({ page }).include('[role="dialog"]').withTags(["wcag2a", "wcag2aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: info.outputPath(`create-availability-${locale}.png`) });
    if (locale === "en") {
      await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
      await submit.scrollIntoViewIfNeeded();
      expect(await dialog.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
      expect(await dialog.locator("form").evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1);
      await page.screenshot({ path: info.outputPath("create-availability-text200.png") });
      await dialog.getByRole("textbox").scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("create-availability-text200-top.png") });
      await page.evaluate(() => { document.documentElement.style.fontSize = ""; });
    }
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(opener).toBeFocused();
  }
});

test("staff use CRM without configuration access and old routes redirect", async ({ page }, info) => {
  const owner = await crmSession(page);
  let bot = (await owner.list<Bot>("bots")).find(bot => bot.scenario === "crm");
  if (!bot) bot = await owner.create<Bot>("bots", { name: "Staff CRM", scenario: "crm" });
  if (bot.status !== "active") await owner.action(`bots/${bot.id}/activate`);
  await page.context().clearCookies();
  await page.evaluate(() => localStorage.clear());
  const session = await crmSession(page, "business_manager@example.com");
  await page.goto("/app/ai-assistant");
  await expect(page).toHaveURL(new RegExp(`/ai-agents/${bot.id}/work$`));
  await expect(page.getByRole("textbox", { name: "Сообщение агенту", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Профиль", exact: true })).toHaveCount(0);
  await expect(page.locator('[data-focus-return-id="ai-agent-create"]')).toHaveCount(0);
  const directory = await session.read("ai/agents", { business: session.business });
  expect(directory[0].settings_json).toBeUndefined();
  await page.screenshot({ path: info.outputPath("staff-workspace.png"), fullPage: true });
});
