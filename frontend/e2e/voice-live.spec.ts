import { readFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const fixture = process.env.VOICE_REVIEW_FIXTURE ? JSON.parse(readFileSync(process.env.VOICE_REVIEW_FIXTURE, "utf8")) : null;
test.beforeEach(() => test.skip(!fixture?.threads.live || process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated live voice fixtures"));

async function mockStream(page: Page, fail = false) {
  let chunks = 0, closed = false;
  await page.route("**/api/ai/speech/?*", async route => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...(await response.json()), realtime_ready: true } });
  });
  await page.route("**/api/ai/speech/session/", route => route.fulfill({ json: { token: "synthetic-single-use-token", max_seconds: 60 } }));
  await page.routeWebSocket("wss://api.elevenlabs.io/**", socket => {
    expect(new URL(socket.url()).searchParams.get("enable_logging")).toBe("false");
    socket.send(JSON.stringify({ message_type: "session_started" }));
    socket.onClose(() => { closed = true; });
    socket.onMessage(message => {
      const data = JSON.parse(String(message));
      if (data.commit) socket.send(JSON.stringify({ message_type: "committed_transcript", text: "Толық аты-жөні Әсел Сынақ" }));
      else if (++chunks === 1) socket.send(JSON.stringify({ message_type: "partial_transcript", text: "Толық аты-жөні Әсел" }));
      else if (chunks === 3) socket.send(JSON.stringify(fail
        ? { message_type: "rate_limited", error: "private provider detail" }
        : { message_type: "partial_transcript", text: "Толық аты-жөні Әсел Сынақ" }));
    });
  });
  return { isClosed: () => closed };
}

test("live words precede stop, final remains editable and CRM requires fresh approval", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const session = await crmSession(page, fixture.email);
  const before = await session.list("appointments");
  await page.evaluate(({ key, thread }) => { localStorage.setItem("ai_smb_language", "ru"); sessionStorage.setItem(key, thread); },
    { key: `voice-thread:v2:${fixture.user}:${fixture.business}`, thread: fixture.threads.live });
  await mockStream(page);
  await page.goto("/app/clients");
  const trigger = page.getByRole("button", { name: ru["voice.title"], exact: true });
  await trigger.click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await panel.getByRole("button", { name: ru["voice.record"], exact: true }).click();
  await expect(panel.getByTestId("voice-live-transcript")).toHaveText("Толық аты-жөні Әсел Сынақ");
  await expect(panel.getByRole("button", { name: ru["voice.stop"], exact: true })).toBeVisible();
  expect((await session.list("appointments")).length).toBe(before.length);
  await page.screenshot({ path: info.outputPath("live-words-390.png"), fullPage: true });
  await panel.getByRole("button", { name: ru["voice.stop"], exact: true }).click();
  const input = panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true });
  await expect(input).toHaveValue("Толық аты-жөні Әсел Сынақ");
  await expect(input).toBeFocused();
  await input.fill("Толық аты-жөні Әсел Сынақ, пожалуйста");
  expect((await session.list("appointments")).length).toBe(before.length);
  await page.screenshot({ path: info.outputPath("live-edit-390.png"), fullPage: true });
  await panel.getByRole("button", { name: ru["agentChat.send"], exact: true }).click();
  const confirm = panel.getByRole("button", { name: ru["agentChat.confirm"], exact: true });
  await expect(confirm).toBeEnabled();
  await expect(panel).toContainText("Әсел Сынақ");
  await expect(panel).toContainText("09:00");
  expect((await session.list("appointments")).length).toBe(before.length);
  await confirm.focus(); await page.keyboard.press("Enter");
  await expect.poll(async () => (await session.list("appointments")).length).toBe(before.length + 1);
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});

test("interrupted stream retains partial for explicit editing, no automatic command", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await crmSession(page, fixture.email);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  const stream = await mockStream(page, true);
  await page.goto("/app/clients");
  await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await panel.getByRole("button", { name: ru["voice.record"], exact: true }).click();
  await expect(panel).toContainText(ru["voice.liveInterrupted"]);
  await expect(panel).not.toContainText("private provider detail");
  await expect.poll(stream.isClosed).toBe(true);
  await page.screenshot({ path: info.outputPath("live-error-390.png"), fullPage: true });
  await panel.getByRole("button", { name: ru["voice.editRequest"], exact: true }).last().click();
  await expect(panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true })).toHaveValue("Толық аты-жөні Әсел");
});

for (const [locale, width, copy] of [["ru", 1440, ru], ["kk", 768, kk], ["en", 390, en]] as const) {
  test(`live panel ${locale} ${width} closes microphone and returns focus`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await crmSession(page, fixture.email);
    await page.evaluate(locale => localStorage.setItem("ai_smb_language", locale), locale);
    const stream = await mockStream(page);
    await page.goto("/app/clients");
    const trigger = page.getByRole("button", { name: copy["voice.title"], exact: true });
    await trigger.click();
    const panel = page.getByRole("dialog", { name: copy["voice.title"], exact: true });
    await panel.getByRole("button", { name: copy["voice.record"], exact: true }).click();
    await expect(panel.getByTestId("voice-live-transcript")).toHaveText("Толық аты-жөні Әсел Сынақ");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`live-${locale}-${width}.png`), fullPage: true });
    await page.keyboard.press("Escape");
    await expect.poll(stream.isClosed).toBe(true);
    await expect(trigger).toBeFocused();
  });
}

test("microphone denial closes the issued stream and keeps text input usable", async ({ page }) => {
  await crmSession(page, fixture.email);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException("Denied", "NotAllowedError"); };
  });
  const stream = await mockStream(page);
  await page.goto("/app/clients");
  await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await panel.getByRole("button", { name: ru["voice.record"], exact: true }).click();
  await expect(panel).toContainText(ru["voice.error.permission"]);
  await expect.poll(stream.isClosed).toBe(true);
  await panel.getByRole("button", { name: ru["voice.typeInstead"], exact: true }).click();
  await expect(panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true })).toBeEditable();
});

test("batch fallback also requires transcript review before sending", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await crmSession(page, fixture.email);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  let commands = 0;
  page.on("request", request => { if (request.method() === "POST" && request.url().endsWith("/turns/")) commands++; });
  await page.route("**/api/ai/speech/?*", async route => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...(await response.json()), ready: true, realtime_ready: false } });
  });
  await page.route("**/api/ai/speech/", route => route.fulfill({ json: { text: "Создай задачу позвонить клиенту завтра" } }));
  await page.goto("/app/clients");
  await page.getByRole("button", { name: ru["voice.title"], exact: true }).click();
  const panel = page.getByRole("dialog", { name: ru["voice.title"], exact: true });
  await expect(panel).toContainText(ru["voice.batchTranscription"]);
  await panel.getByRole("button", { name: ru["voice.record"], exact: true }).click();
  await panel.getByRole("button", { name: ru["voice.stop"], exact: true }).click();
  await expect(panel.getByRole("textbox", { name: ru["voice.transcript"], exact: true })).toHaveValue("Создай задачу позвонить клиенту завтра");
  expect(commands).toBe(0);
  await page.screenshot({ path: info.outputPath("batch-review-390.png") });
});
