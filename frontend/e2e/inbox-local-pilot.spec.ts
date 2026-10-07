import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable local pilot fixtures required");
  test.setTimeout(180_000);
});

test("customer setup uses safe defaults, one booking control and a persistent atomic save", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<{ id: number }>("bots", { name: "Local pilot receptionist" });
  await page.goto(`/app/ai-agents/${bot.id}/profile`);
  const editor = page.getByTestId("ai-agent-editor");
  await expect(editor.getByRole("textbox", { name: ru["aiAgents.systemPrompt"], exact: true })).toHaveValue(ru["aiSetup.dentalPrompt"]);
  await expect(editor.getByRole("slider")).not.toBeVisible();
  const advanced = editor.locator("summary").filter({ hasText: ru["aiSetup.advanced"] });
  await advanced.focus();
  await advanced.press("Enter");
  await expect(editor.getByRole("slider")).toBeVisible();
  await advanced.press("Enter");
  await editor.getByRole("tab", { name: "Действия", exact: true }).click();
  const mode = editor.getByLabel(ru["aiAgents.control.mode"], { exact: true });
  const booking = editor.getByRole("switch", { name: ru["aiAgents.functions.bookingTitle"], exact: true });
  const policy = editor.getByLabel(ru["aiAgents.creationPolicy"], { exact: true });
  await expect(booking).toBeDisabled();
  await expect(policy).toBeDisabled();
  await mode.click();
  await page.getByRole("option", { name: ru["aiAgents.control.mode.triage"], exact: true }).click();
  await expect(booking).toBeDisabled();
  await expect(policy).toBeDisabled();
  await editor.getByRole("switch", { name: ru["aiAgents.control.autoReplyTitle"], exact: true }).check();
  await mode.click();
  await page.getByRole("option", { name: ru["aiAgents.control.mode.leadTask"], exact: true }).click();
  await expect(booking).toBeEnabled();
  await expect(booking).not.toBeChecked();
  await booking.check();
  await policy.click();
  await page.getByRole("option", { name: ru["aiAgents.authority.automatic"], exact: true }).click();
  const save = editor.getByRole("button", { name: "Сохранить изменения", exact: true });
  await save.click();
  await expect(save).toBeDisabled();
  const stored = await session.read(`bots/${bot.id}`);
  expect(stored.settings_json.auto_crm_pipeline).toMatchObject({ mode: "lead_task", enabled: true,
    creation_policy: "automatic", auto_send_reply: true, create_appointment: true });
  const profiles = await session.list<{ bot: number; allowed_tools_json: { tools: string[] } }>("ai/agent-profiles");
  expect(profiles.find(item => item.bot === bot.id)?.allowed_tools_json.tools).toContain("create_appointment");
  await page.reload();
  await expect(booking).toBeChecked();
  await booking.uncheck();
  await save.click();
  await expect(save).toBeDisabled();
  expect((await session.read(`bots/${bot.id}`)).settings_json.auto_crm_pipeline.create_appointment).toBe(false);
  expect((await session.list<{ bot: number; allowed_tools_json: { tools: string[] } }>("ai/agent-profiles"))
    .find(item => item.bot === bot.id)?.allowed_tools_json.tools).not.toContain("create_appointment");
  // Changing the processing mode must never silently grant booking permission.
  await mode.click();
  await page.getByRole("option", { name: ru["aiAgents.control.mode.triage"], exact: true }).click();
  await expect(booking).not.toBeChecked();
  await expect(booking).toBeDisabled();
  await save.click();
  await expect(save).toBeDisabled();
  expect((await session.read(`bots/${bot.id}`)).settings_json.auto_crm_pipeline.create_appointment).toBe(false);
  await page.screenshot({ path: info.outputPath("customer-actions.png"), fullPage: true });
});

test("profile and safety settings remain accessible in each locale and viewport", async ({ page }, info) => {
  const session = await crmSession(page);
  const bot = await session.create<{ id: number }>("bots", { name: "Local pilot settings" });
  for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    for (const section of ["profile", "actions"]) {
      await page.goto(`/app/ai-agents/${bot.id}/${section}`);
      const editor = page.getByTestId("ai-agent-editor");
      const summary = editor.locator("summary").filter({ hasText: copy[section === "profile" ? "aiSetup.advanced" : "customerSafety.processingLimits"] });
      await expect(summary).toBeVisible();
      await summary.focus();
      await summary.press("Enter");
      if (section === "profile") await expect(editor.getByRole("slider")).toBeVisible();
      else await expect(editor.getByRole("spinbutton", { name: copy["customerSafety.callLimit"], exact: true })).toHaveValue("30");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      expect((await new AxeBuilder({ page }).include('[data-testid="ai-agent-editor"]').analyze()).violations).toEqual([]);
      await page.screenshot({ path: info.outputPath(`${locale}-${section}.png`), fullPage: true });
    }
  }
});
