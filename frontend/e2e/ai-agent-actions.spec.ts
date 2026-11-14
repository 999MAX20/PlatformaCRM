import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { aiAgents as ru } from "../src/lib/i18n/ru/aiAgents";
import { aiAgents as kk } from "../src/lib/i18n/kk/aiAgents";
import { aiAgents as en } from "../src/lib/i18n/en/aiAgents";
import type { Bot } from "../src/types";

for (const locale of ["ru", "kk", "en"] as const) {
  test(`actions localized keyboard and layout ${locale}`, async ({ page }, info) => {
    test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable API required");
    const session = await crmSession(page);
    const dict = { ru, kk, en }[locale];
    const bot = await session.create<Bot>("bots", { name: "Actions acceptance", status: "draft", settings_json: {
      auto_crm_pipeline: { mode: "customer_actions", enabled: true, auto_send_reply: false,
        task_creation_policy: "staff_confirmation", appointment_creation_policy: "staff_confirmation", create_appointment: true },
      customer_safety: { allow_first_off_topic: false, off_topic_handoff_after: 2 },
    } });
    try {
      await session.create("ai/agent-profiles", { bot: bot.id, name: bot.name, is_active: true,
        role_description: "Administrator", allowed_tools_json: { tools: ["create_client", "create_task", "create_appointment"] } });
      await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
      await page.goto(`/app/ai-agents/${bot.id}/actions`);
      const editor = page.getByTestId("ai-agent-editor");
      await expect(editor).toBeVisible();
      const task = editor.getByRole("combobox").nth(0);
      await task.focus();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("listbox")).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(task).toBeFocused();
      await expect(page.getByRole("listbox")).toHaveCount(0);
      const offTopic = editor.getByRole("combobox").nth(2);
      await expect(offTopic).toContainText(dict["aiAgents.actions.offTopicSaved"].replace("{count}", "2"));
      await offTopic.click();
      await expect(page.getByRole("option")).toHaveCount(4);
      await page.getByRole("option", { name: dict["aiAgents.actions.offTopic2"], exact: true }).click();
      await expect(offTopic).toBeFocused();
      await expect(offTopic).toContainText(dict["aiAgents.actions.offTopic2"]);
      await page.locator("summary").filter({ hasText: /Лимиты|шектеу|limits/i }).click();
      await expect(editor.getByRole("spinbutton")).toHaveCount(5);
      for (const zoom of locale === "ru" ? [100, 200] : [100]) {
        await page.evaluate(value => { document.documentElement.style.fontSize = `${value}%`; window.scrollTo(0, 0); }, zoom);
        await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
        await page.screenshot({ path: info.outputPath(`${locale}-${zoom}-top.png`) });
        await offTopic.scrollIntoViewIfNeeded();
        await offTopic.click();
        await expect(page.getByRole("listbox")).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(offTopic).toBeFocused();
        await page.screenshot({ path: info.outputPath(`${locale}-${zoom}-safety.png`) });
        await editor.getByRole("textbox").last().scrollIntoViewIfNeeded();
        await page.screenshot({ path: info.outputPath(`${locale}-${zoom}-bottom.png`) });
      }
      const results = await new AxeBuilder({ page }).include('[data-testid="ai-agent-editor"]').withTags(["wcag2a", "wcag2aa"]).analyze();
      expect(results.violations).toEqual([]);
    } finally {
      const response = await page.request.delete(`${process.env.E2E_API_BASE_URL}/api/bots/${bot.id}/`, { headers: session.headers });
      expect(response.ok()).toBeTruthy();
    }
  });
}
