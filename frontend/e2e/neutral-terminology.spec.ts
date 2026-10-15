import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test("neutral resource presets and new customer AI profiles work in all locales", async ({ page }, info) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable API fixtures");
  test.setTimeout(120_000);
  const session = await crmSession(page);
  for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/app/business/resources");
    const preset = page.getByRole("combobox", { name: copy["resources.quickCreate"], exact: true });
    await preset.click();
    await page.getByRole("option", { name: copy["resources.templateChair"], exact: true }).click();
    await page.getByRole("button", { name: copy["resources.useTemplate"], exact: true }).click();
    const resourceDialog = page.getByRole("dialog");
    await expect(resourceDialog.getByRole("textbox", { name: copy["resources.name"], exact: true })).toHaveValue(copy["resources.templateChairName"]);
    await page.screenshot({ path: info.outputPath(`neutral-resource-${language}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    await expect(resourceDialog).toHaveCount(0);

    const bot = await session.create<{ id: number }>("bots", {
      name: `Neutral ${language} ${info.project.name}`, status: "draft", scenario: "inbox", default_language: language,
    });
    await page.goto(`/app/ai-agents/${bot.id}/profile`);
    const editor = page.getByTestId("ai-agent-editor");
    await expect(editor.getByRole("textbox", { name: copy["aiAgents.roleDescription"], exact: true })).toHaveValue(copy["aiSetup.dentalRole"]);
    await expect(editor.getByRole("textbox", { name: copy["aiAgents.systemPrompt"], exact: true })).toHaveValue(copy["aiSetup.dentalPrompt"]);
    const template = editor.getByRole("button", { name: copy["aiWorkspace.template"], exact: true });
    await template.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toContainText(copy["aiSetup.dentalRole"]);
    await page.keyboard.press("Escape");
    await expect(template).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`neutral-agent-${language}.png`), fullPage: true });
  }
});
