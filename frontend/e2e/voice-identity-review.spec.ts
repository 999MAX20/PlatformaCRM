import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const fixture = process.env.VOICE_REVIEW_FIXTURE ? JSON.parse(readFileSync(process.env.VOICE_REVIEW_FIXTURE, "utf8")) : null;
test.beforeEach(() => test.skip(!fixture || process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated voice review fixtures"));

for (const [language, dictionary, width] of [["ru", ru, 1440], ["kk", kk, 320], ["en", en, 390]] as const) {
  test(`new client review ${language}: visible identity, keyboard, real confirmation or cancellation`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const session = await crmSession(page, fixture.email);
    const before = await session.list("clients");
    await page.evaluate(({ language, key, thread }) => {
      localStorage.setItem("ai_smb_language", language); sessionStorage.setItem(key, thread);
    }, { language, key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread: fixture.threads[language] });
    await page.goto("/app/clients");
    await page.getByRole("button", { name: dictionary["voice.title"], exact: true }).click();
    const panel = page.getByRole("dialog", { name: dictionary["voice.title"], exact: true });
    await expect(panel).toContainText(dictionary["voice.reviewIdentity"]);
    await expect(panel).toContainText("+77011111111");
    expect((await session.list("clients")).length).toBe(before.length);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`identity-${language}-${width}.png`), fullPage: true });
    const button = panel.getByRole("button", { name: dictionary[language === "en" ? "aiCRM.discard" : "agentChat.confirm"], exact: true });
    await button.focus(); await expect(button).toBeFocused(); await page.keyboard.press("Enter");
    await expect.poll(async () => (await session.read(`ai/conversations/${fixture.threads[language]}`)).turns.at(-1).status).toBe(language === "en" ? "cancelled" : "completed");
    expect((await session.list("clients")).length).toBe(before.length + (language === "en" ? 0 : 1));
  });
}

test("correct identity, retained input on outage, stale proposal rejection and confirmation replay", async ({ page }) => {
  const session = await crmSession(page, fixture.email);
  const before = await session.list("clients");
  await page.evaluate(({ key, thread }) => { localStorage.setItem("ai_smb_language", "ru"); sessionStorage.setItem(key, thread); },
    { key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread: fixture.threads.edit });
  await page.goto("/app/clients");
  await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await panel.getByRole("button", { name: ru["voice.editRequest"], exact: true }).click();
  const input = panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true });
  await expect(input).toBeFocused();
  const corrected = "Create client Әлихан Омаров phone +77012345678";
  await input.fill(corrected);
  await page.route("**/api/ai/conversations/*/turns/", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary test outage" }) }));
  await panel.getByRole("button", { name: ru["agentChat.send"], exact: true }).click();
  await expect(input).toHaveValue(corrected);
  expect((await session.list("clients")).length).toBe(before.length);
  await page.unroute("**/api/ai/conversations/*/turns/");
  await panel.getByRole("button", { name: ru["agentChat.send"], exact: true }).click();
  await expect(panel).toContainText("Әлихан Омаров");
  await expect(panel).toContainText("+77012345678");
  await expect(panel.getByRole("button", { name: ru["agentChat.confirm"], exact: true })).toBeEnabled();
  const pending = await session.read(`ai/conversations/${fixture.threads.edit}`);
  expect(pending.turns[0].status).toBe("superseded");
  expect((await session.list("clients")).length).toBe(before.length);
  const latest = pending.turns.at(-1);
  await panel.getByRole("button", { name: ru["agentChat.confirm"], exact: true }).click();
  await expect.poll(async () => (await session.read(`ai/conversations/${fixture.threads.edit}`)).turns.at(-1).status).toBe("completed");
  await session.action(`ai/conversations/${fixture.threads.edit}/turns/${latest.id}/confirm`, {
    expected_revision: pending.conversation.revision, actions: latest.actions.map((action: { id: number; fingerprint: string }) => ({ id: action.id, fingerprint: action.fingerprint })),
  });
  const clients = await session.list<{ full_name: string; phone: string }>("clients");
  expect(clients.length).toBe(before.length + 1);
  expect(clients.some(client => client.full_name === "Әлихан Омаров" && client.phone === "+77012345678")).toBe(true);
});

test("Kazakh task title can be corrected and reviewed before any task is created", async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 844 });
  const session = await crmSession(page, fixture.email);
  const before = await session.list("tasks");
  await page.evaluate(({ key, thread }) => { localStorage.setItem("ai_smb_language", "kk"); sessionStorage.setItem(key, thread); },
    { key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread: fixture.threads.task });
  await page.goto("/app/tasks");
  await page.getByRole("button", { name: kk["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: kk["voice.title"], exact: true });
  await expect(panel).toContainText(kk["voice.reviewTask"]);
  expect((await session.list("tasks")).length).toBe(before.length);
  await panel.getByRole("button", { name: kk["voice.editRequest"], exact: true }).click();
  await panel.getByRole("textbox", { name: kk["voice.transcript"], exact: true }).fill("Create task Ертең клиентке қоңырау шалу");
  await panel.getByRole("button", { name: kk["agentChat.send"], exact: true }).click();
  await expect(panel).toContainText("Ертең клиентке қоңырау шалу");
  await expect(panel.getByRole("button", { name: kk["agentChat.confirm"], exact: true })).toBeEnabled();
  expect((await session.list("tasks")).length).toBe(before.length);
  await page.screenshot({ path: info.outputPath("task-review-kk320.png"), fullPage: true });
  const confirm = panel.getByRole("button", { name: kk["agentChat.confirm"], exact: true });
  await confirm.focus(); await page.keyboard.press("Enter");
  await expect.poll(async () => (await session.read(`ai/conversations/${fixture.threads.task}`)).turns.at(-1).status).toBe("completed");
  const tasks = await session.list<{ title: string }>("tasks");
  expect(tasks.length).toBe(before.length + 1);
  expect(tasks.some(task => task.title === "Ертең клиентке қоңырау шалу")).toBe(true);
});
