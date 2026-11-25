import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";

const fixture = process.env.VOICE_REVIEW_FIXTURE ? JSON.parse(readFileSync(process.env.VOICE_REVIEW_FIXTURE, "utf8")) : null;
test.beforeEach(() => test.skip(!fixture || process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated voice review fixtures"));

test("locale default preserves explicitly selected automatic detection", async ({ page }) => {
  await crmSession(page, fixture.email);
  await page.evaluate(user => { localStorage.setItem("ai_smb_language", "kk"); localStorage.removeItem(`voice-preferences:${user}`); }, fixture.user);
  await page.goto("/app/settings/voice");
  const language = page.getByLabel(kk["voice.language"], { exact: true });
  await expect(language).toContainText("Қазақша");
  await language.click();
  await page.getByRole("option", { name: kk["voice.auto"], exact: true }).click();
  await page.reload();
  await expect(language).toContainText(kk["voice.auto"]);
});

for (const [label, width] of [["existing", 1440], ["cancel", 320], ["reschedule", 390]] as const) {
  test(`${label} appointment requires visible review before mutation`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const session = await crmSession(page, fixture.email);
    await page.evaluate(({ key, thread }) => {
      localStorage.setItem("ai_smb_language", "ru"); sessionStorage.setItem(key, thread);
    }, { key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread: fixture.threads[label] });
    const before = await session.list<{ id: number; start_at: string; status: string }>("appointments");
    await page.goto("/app/clients");
    await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
    const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
    await expect(panel).toContainText("Әсем Тестова");
    await expect(panel).toContainText("2030");
    expect((await session.read(`ai/conversations/${fixture.threads[label]}`)).turns.at(-1).status).toBe("awaiting_confirmation");
    expect(await session.list("appointments")).toEqual(before);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const action = panel.getByRole("button", { name: ru[label === "cancel" ? "aiCRM.discard" : "agentChat.confirm"], exact: true });
    await action.focus(); await expect(action).toBeFocused();
    await page.screenshot({ path: info.outputPath(`voice-${label}-${width}.png`), fullPage: true });
    await page.keyboard.press("Enter");
    await expect.poll(async () => (await session.read(`ai/conversations/${fixture.threads[label]}`)).turns.at(-1).status).toBe(label === "cancel" ? "cancelled" : "completed");
    const after = await session.list<{ id: number; start_at: string; status: string }>("appointments");
    if (label === "existing") expect(after.length).toBe(before.length + 1);
    if (label === "cancel") expect(after).toEqual(before);
    if (label === "reschedule") expect(after.find(row => row.id === fixture.reschedule_appointment)?.start_at).toContain("2030-11-08T13:00:00");
  });
}

test("recording sends KK profile and only opted-in card reference", async ({ page }) => {
  await crmSession(page, fixture.email);
  await page.evaluate(user => { localStorage.setItem("ai_smb_language", "kk"); localStorage.removeItem(`voice-preferences:${user}`); }, fixture.user);
  const uploads: string[] = [];
  await page.route("**/api/ai/speech/", async route => {
    if (route.request().method() !== "POST") return route.continue();
    uploads.push(route.request().postData() || "");
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "speech_timeout", retryable: true }) });
  });
  for (const context of [false, true]) {
    await page.goto(`/app/clients/${fixture.client}`);
    await expect(page.getByRole("heading", { name: "Әсем Тестова", exact: true })).toBeVisible();
    await page.getByRole("button", { name: kk["voice.title"], exact: true }).click();
    const panel = page.getByRole("dialog", { name: kk["voice.title"], exact: true });
    if (context) await panel.getByRole("checkbox").check();
    const record = panel.getByRole("button", { name: kk["voice.record"], exact: true });
    await expect(record).toBeEnabled();
    await record.click();
    const send = panel.getByRole("button", { name: kk["voice.stop"], exact: true });
    await expect(send).toBeVisible();
    await page.waitForTimeout(600);
    await send.click();
    await expect.poll(() => uploads.length).toBe(context ? 2 : 1);
    const body = uploads.at(-1)!;
    expect(body).toMatch(/name="language"\r\n\r\nkk/);
    expect(body.includes('name="current_entity"')).toBe(context);
    if (context) expect(body).toContain(JSON.stringify({ entity: "clients", id: fixture.client }));
    await expect(panel.getByRole("button", { name: kk["voice.discardRecording"], exact: true })).toBeVisible();
    await panel.getByRole("button", { name: kk["voice.discardRecording"], exact: true }).click();
  }
});
