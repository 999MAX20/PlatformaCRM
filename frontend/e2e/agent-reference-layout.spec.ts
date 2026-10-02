import fs from "node:fs";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";

test("reference agent workspace keeps five sections and header usable across sizes and languages", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable fixtures");
  test.setTimeout(240_000);
  const session = await crmSession(page);
  const bot = await session.create<{ id: number }>("bots", { name: "Администратор клиники", status: "draft", default_language: "ru" });
  await session.create("ai/agent-profiles", {
    bot: bot.id, name: "Администратор клиники", role_description: "Помогает клиентам узнать об услугах и передаёт заявки администратору.",
    tone: "friendly", language: "ru", is_active: true, system_prompt: "Используйте сведения компании.",
    rules_json: [], allowed_tools_json: { tools: ["handoff_to_manager"] }, escalation_rules_json: [],
  });
  const sizes = testInfo.project.name === "mobile-chromium" ? [{ width: 393, height: 851 }]
    : testInfo.project.name === "tablet-chromium" ? [{ width: 1024, height: 768 }]
    : [{ width: 1280, height: 720 }, { width: 1600, height: 900 }];
  const evidence = [];
  for (const size of sizes) {
    await page.setViewportSize(size);
    for (const section of ["profile", "knowledge", "actions", "channels", "test"]) {
      await page.goto(`/app/ai-agents/${bot.id}/${section}`);
      const editor = page.getByTestId("ai-agent-editor");
      await expect(editor).toBeVisible();
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.fonts.ready);
      const geometry = await editor.evaluate(node => {
        const bounds = (element: Element | null) => element?.getBoundingClientRect().toJSON();
        return { editor: bounds(node), header: bounds(node.querySelector("header")), footer: bounds(node.querySelector("footer")), panel: bounds(node.querySelector('[role="tabpanel"]')), overflow: document.documentElement.scrollWidth - innerWidth };
      });
      const selected = await editor.getByRole("tab", { selected: true }).boundingBox();
      const tabs = await editor.getByRole("tablist").boundingBox();
      expect(selected!.x).toBeGreaterThanOrEqual(tabs!.x - 1);
      expect(selected!.x + selected!.width).toBeLessThanOrEqual(tabs!.x + tabs!.width + 1);
      expect(geometry.overflow).toBeLessThanOrEqual(1);
      expect(geometry.editor.bottom).toBeLessThanOrEqual(size.height + 1);
      const violations = (await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze()).violations;
      expect(violations, `${size.width}/${section}`).toEqual([]);
      evidence.push({ size, section, geometry, violations });
      if (size.width >= 1280) {
        expect(geometry.header.height).toBeLessThanOrEqual(105);
        expect(geometry.panel.height).toBeGreaterThanOrEqual(490);
        expect(geometry.editor.x).toBe(64);
        expect(geometry.editor.width).toBe(size.width - 64);
        const picker = await page.getByTestId("agent-header-picker").boundingBox();
        const title = await page.getByRole("banner").getByText("ИИ-агенты", { exact: true }).filter({ visible: true }).boundingBox();
        const search = await page.getByRole("banner").getByRole("textbox", { name: "Поиск", exact: true }).boundingBox();
        expect(picker!.width).toBe(180);
        expect(picker!.x).toBeGreaterThan(title!.x + title!.width);
        expect(picker!.x + picker!.width).toBeLessThan(search!.x);
        if (section === "profile") {
          const preset = await editor.getByRole("button", { name: "Применить роль администратора стоматологии", exact: true }).boundingBox();
          expect(preset!.height).toBeLessThanOrEqual(42);
        }
        if (section === "test") {
          const submit = await editor.getByRole("button", { name: "Проверить ответ", exact: true }).boundingBox();
          expect(submit!.y + submit!.height).toBeLessThanOrEqual(size.height);
        }
      }
      await page.screenshot({ path: testInfo.outputPath(`${size.width}-${section}.png`), animations: "disabled" });
      if (size.width < 1024 && section === "profile") {
        const banner = page.getByRole("banner");
        await banner.getByRole("button", { name: "Поиск", exact: true }).click();
        const search = await banner.getByRole("textbox", { name: "Поиск", exact: true }).boundingBox();
        const picker = await page.getByTestId("agent-header-picker").boundingBox();
        expect(search!.y).toBeGreaterThanOrEqual(0);
        expect(search!.y + search!.height).toBeLessThanOrEqual(picker!.y);
        const create = await banner.getByRole("button", { name: "Создать агента", exact: true }).boundingBox();
        expect(search!.x + search!.width).toBeLessThanOrEqual(create!.x);
        await page.screenshot({ path: testInfo.outputPath("mobile-global-search.png") });
        await page.keyboard.press("Escape");
      }
      if (section === "profile") {
        await editor.getByRole("button", { name: "Дополнительные настройки", exact: true }).click();
        await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toBeEnabled();
        await page.screenshot({ path: testInfo.outputPath(`${size.width}-profile-advanced.png`) });
      }
    }
  }
  for (const locale of ["kk", "en", "ru"]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    for (const section of ["profile", "knowledge", "actions", "channels", "test"]) {
      await page.goto(`/app/ai-agents/${bot.id}/${section}`);
      const editor = page.getByTestId("ai-agent-editor");
      await expect(editor).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await page.evaluate(() => document.fonts.ready);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      expect(await editor.evaluate(element => getComputedStyle(element).fontFamily)).toContain(locale === "kk" ? "Noto Sans Variable" : "Manrope Variable");
      await page.screenshot({ path: testInfo.outputPath(`${locale}-${section}.png`), animations: "disabled" });
    }
  }
  fs.writeFileSync(testInfo.outputPath("layout-evidence.json"), JSON.stringify(evidence, null, 2));
});
