import fs from "node:fs";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";

test("centered agent workspace keeps natural flow and all five sections usable across sizes and languages", async ({ page }, testInfo) => {
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
    : [{ width: 1280, height: 720 }, { width: 1600, height: 900 }, { width: 1848, height: 1000 }];
  const evidence = [];
  for (const size of sizes) {
    await page.setViewportSize(size);
    const searchBoxes = [];
    for (const route of ["/app/clients", "/app/tasks", `/app/ai-agents/${bot.id}/profile`]) {
      await page.goto(route);
      const banner = page.getByRole("banner");
      const search = size.width >= 1024
        ? banner.getByRole("textbox", { name: "Поиск", exact: true })
        : banner.getByRole("button", { name: "Поиск", exact: true });
      await expect(search).toBeVisible();
      searchBoxes.push(await search.boundingBox());
      expect((await banner.boundingBox())!.height).toBe(57);
    }
    for (const box of searchBoxes.slice(1)) {
      for (const key of ["x", "y", "width", "height"] as const) {
        expect(Math.abs(box![key] - searchBoxes[0]![key])).toBeLessThanOrEqual(1);
      }
    }
    for (const section of ["profile", "knowledge", "actions", "channels", "test"]) {
      await page.goto(`/app/ai-agents/${bot.id}/${section}`);
      const editor = page.getByTestId("ai-agent-editor");
      await expect(editor).toBeVisible();
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.fonts.ready);
      const geometry = await editor.evaluate(node => {
        const bounds = (element: Element | null) => element?.getBoundingClientRect().toJSON();
        return { editor: bounds(node), header: bounds(node.querySelector("header")), footer: bounds(node.querySelector("footer")), panel: bounds(node.querySelector('[role="tabpanel"]')), fields: bounds(node.querySelector("fieldset")), tabs: bounds(node.querySelector('[role="tablist"]')), overflow: document.documentElement.scrollWidth - innerWidth };
      });
      const selected = await editor.getByRole("tab", { selected: true }).boundingBox();
      const tabs = await editor.getByRole("tablist").boundingBox();
      expect(selected!.x).toBeGreaterThanOrEqual(tabs!.x - 1);
      expect(selected!.x + selected!.width).toBeLessThanOrEqual(tabs!.x + tabs!.width + 1);
      expect(geometry.overflow).toBeLessThanOrEqual(1);
      const navigation = await page.getByTestId("agent-navigation").boundingBox();
      if (size.width >= 1280) {
        expect(navigation!.x).toBeGreaterThanOrEqual(64);
        expect(navigation!.x + navigation!.width).toBeLessThanOrEqual(geometry.editor.x - 16);
      } else {
        expect(navigation!.y + navigation!.height).toBeLessThanOrEqual(geometry.editor.y);
      }
      await expect(page.getByRole("banner").getByRole("button", { name: "Создать агента", exact: true })).toHaveCount(0);
      const workspaceLeft = size.width >= 1024 ? 64 : 0;
      const leftMargin = geometry.editor.x - workspaceLeft;
      const rightMargin = size.width - geometry.editor.right;
      expect(Math.abs(leftMargin - rightMargin)).toBeLessThanOrEqual(1);
      expect(geometry.editor.width).toBeLessThanOrEqual(960);
      expect(leftMargin).toBeGreaterThanOrEqual(12);
      for (const aligned of [geometry.header, geometry.tabs, geometry.panel, geometry.fields, geometry.footer].filter(Boolean)) {
        expect(Math.abs(aligned.x - geometry.editor.x)).toBeLessThanOrEqual(1);
        expect(Math.abs(aligned.width - geometry.editor.width)).toBeLessThanOrEqual(1);
      }
      if (geometry.footer) {
        expect(Math.abs(geometry.footer.y - geometry.panel.bottom)).toBeLessThanOrEqual(1);
        expect(geometry.panel.bottom - geometry.fields.bottom).toBeLessThanOrEqual(24);
      }
      const violations = (await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze()).violations;
      expect(violations, `${size.width}/${section}`).toEqual([]);
      evidence.push({ size, section, geometry, violations });
      if (size.width >= 1280) {
        expect(geometry.header.height).toBeLessThanOrEqual(105);
        expect(geometry.editor.width).toBe(960);
        if (section === "profile") {
          const preset = await editor.getByRole("button", { name: "Применить роль администратора стоматологии", exact: true }).boundingBox();
          expect(preset!.height).toBeGreaterThanOrEqual(36);
          expect(preset!.height).toBeLessThanOrEqual(40);
          const role = editor.getByRole("textbox", { name: "Описание роли", exact: true });
          expect((await role.boundingBox())!.height).toBe(80);
          expect(await role.evaluate(element => getComputedStyle(element).resize)).toBe("vertical");
          for (const name of ["Название", "Язык", "Тон"]) {
            const control = editor.getByLabel(name, { exact: true });
            const box = (await control.boundingBox())!;
            expect(box.height).toBeGreaterThanOrEqual(36);
            expect(box.height).toBeLessThanOrEqual(40);
          }
        }
        if (section === "test") {
          const submit = await editor.getByRole("button", { name: "Проверить ответ", exact: true }).boundingBox();
          expect(submit!.y + submit!.height).toBeLessThanOrEqual(size.height);
        }
      }
      await page.screenshot({ path: testInfo.outputPath(`${size.width}-${section}.png`), animations: "disabled", fullPage: true });
      if (section === "actions") {
        const descriptions = editor.locator("details");
        await expect(descriptions).toHaveCount(7);
        for (const detail of await descriptions.all()) {
          await detail.locator("summary").click();
          await expect(detail.locator("p").first()).toBeVisible();
        }
        await page.screenshot({ path: testInfo.outputPath(`${size.width}-actions-help.png`), fullPage: true });
        for (const detail of await descriptions.all()) await detail.locator("summary").click();
      }
      if (geometry.footer) {
        const lastAction = editor.locator("footer").getByRole("button").last();
        await lastAction.evaluate(element => element.scrollIntoView({ block: "center" }));
        await expect(lastAction).toBeInViewport();
        const actionBox = (await lastAction.boundingBox())!;
        expect(actionBox.y + actionBox.height).toBeLessThanOrEqual(size.height - (size.width < 1024 ? 88 : 0));
        await page.evaluate(() => window.scrollTo(0, 0));
      }
      if (size.width < 1024 && section === "profile") {
        const banner = page.getByRole("banner");
        await banner.getByRole("button", { name: "Поиск", exact: true }).click();
        const search = await banner.getByRole("textbox", { name: "Поиск", exact: true }).boundingBox();
        expect(search!.y).toBeGreaterThanOrEqual(0);
        const navigation = await page.getByTestId("agent-navigation").boundingBox();
        expect(search!.y + search!.height).toBeLessThanOrEqual(navigation!.y);
        await page.screenshot({ path: testInfo.outputPath("mobile-global-search.png") });
        await page.keyboard.press("Escape");
      }
      if (section === "profile") {
        await editor.getByRole("button", { name: "Дополнительные настройки", exact: true }).click();
        await expect(editor.getByRole("textbox", { name: "Главная инструкция", exact: true })).toBeEnabled();
        await page.screenshot({ path: testInfo.outputPath(`${size.width}-profile-advanced.png`), fullPage: true });
        const save = editor.getByRole("button", { name: "Сохранить изменения", exact: true });
        await save.evaluate(element => element.scrollIntoView({ block: "center" }));
        await expect(save).toBeInViewport();
        await editor.getByRole("textbox", { name: "Главная инструкция", exact: true }).fill(`Проверка длинной формы ${size.width}`);
        await save.click();
        await expect(save).toBeDisabled();
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
