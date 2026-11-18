import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";

const fixture = process.env.VOICE_REVIEW_FIXTURE ? JSON.parse(readFileSync(process.env.VOICE_REVIEW_FIXTURE, "utf8")) : null;
test.beforeEach(() => test.skip(!fixture?.threads.correction || process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated correction fixtures"));

test("short KK name and RU time corrections preserve booking and require fresh review", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const session = await crmSession(page, fixture.email);
  const before = await session.list("appointments");
  const thread = fixture.threads.correction;
  await page.evaluate(({ key, thread }) => {
    localStorage.setItem("ai_smb_language", "ru"); sessionStorage.setItem(key, thread);
  }, { key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread });
  await page.goto("/app/clients");
  await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await expect(panel).toContainText("Әсел");
  for (const text of ["Нет, в 13:00", "Әсел емес, Әсем Сынақ"]) {
    await panel.getByRole("button", { name: ru["voice.editRequest"], exact: true }).click();
    const input = panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true });
    await expect(input).toBeFocused();
    await input.fill(text);
    await panel.getByRole("button", { name: ru["agentChat.send"], exact: true }).click();
    await expect.poll(async () => (await session.read(`ai/conversations/${thread}`)).turns.at(-1).message).toBe(text);
    await expect(panel.getByRole("button", { name: ru["agentChat.confirm"], exact: true })).toBeEnabled();
    expect((await session.list("appointments")).length).toBe(before.length);
  }
  await expect(panel).toContainText("Әсем");
  await expect(panel).toContainText("13:00");
  await expect(panel).toContainText("Consultation");
  await expect(panel).toContainText("Anna");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("short-correction-review-390.png"), fullPage: true });
  const pending = await session.read(`ai/conversations/${thread}`);
  expect(pending.turns.slice(0, -1).every((turn: { status: string }) => turn.status === "superseded")).toBe(true);
  const confirm = panel.getByRole("button", { name: ru["agentChat.confirm"], exact: true });
  await confirm.focus(); await page.keyboard.press("Enter");
  await expect.poll(async () => (await session.read(`ai/conversations/${thread}`)).turns.at(-1).status).toBe("completed");
  expect((await session.list("appointments")).length).toBe(before.length + 1);
  const clients = await session.list<{ full_name: string }>("clients");
  expect(clients.some(client => client.full_name === "Әсем Сынақ")).toBe(true);
});
