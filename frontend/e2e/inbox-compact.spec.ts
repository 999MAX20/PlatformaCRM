import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { InboxConversation } from "../src/api/inbox";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";

test.use({ actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

async function selectAction(page: Page, label: string, menuLabel: string) {
  const header = page.getByTestId("inbox-thread-header");
  const button = header.getByRole("button", { name: label, exact: true });
  if (await button.isVisible()) return button.click();
  await header.getByRole("button", { name: menuLabel, exact: true }).click();
  await page.getByRole("menuitem", { name: label, exact: true }).click();
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`compact tools preserve AI review, keyboard focus and lifecycle actions (${locale})`, async ({ page }, info) => {
    const session = await crmSession(page);
    const original = (await session.list<InboxConversation>("inbox/conversations"))[0];
    let conversation = { ...original, status: "open", bot_enabled: false, handoff_required: false, client_name: "Алина · консультация", ai_safety: null };
    await page.route(`**/api/inbox/conversations/${original.id}/`, route => route.fulfill({ json: conversation }));
    await page.route(/\/api\/inbox\/conversations\/(?:\?.*)?$/, route => route.fulfill({ json: { count: 1, results: [conversation], next: null, previous: null } }));
    const calls: string[] = [];
    for (const [endpoint, change] of [
      ["assign", { assigned_to_email: "operator@example.test" }],
      ["close", { status: "closed" }],
      ["reopen", { status: "open" }],
    ] as const) {
      await page.route(`**/api/inbox/conversations/${original.id}/${endpoint}/`, route => {
        calls.push(endpoint);
        conversation = { ...conversation, ...change };
        return route.fulfill({ json: conversation });
      });
    }
    const longText = "Здравствуйте! В центральном филиале доступны следующие варианты:\n\nЗавтра: 10:00, 12:30 и 16:00.\nВ пятницу: 09:30 и 14:00.\n\nКонсультация длится 30 минут.\nПодскажите, какой день и время вам удобны?";
    let sends = 0;
    await page.route(`**/api/inbox/conversations/${original.id}/messages/**`, route => {
      if (route.request().method() === "POST") sends++;
      return route.fulfill({ json: { count: 2, next: null, previous: null, has_more: false, results: [
        { id: 98001, conversation: original.id, direction: "inbound", sender_type: "client", text: "Здравствуйте! Хочу записаться на консультацию.", status: "sent", created_at: new Date().toISOString(), attachments: [] },
        { id: 98002, conversation: original.id, direction: "outbound", sender_type: "manager", text: longText, status: "sent", created_at: new Date().toISOString(), attachments: [] },
      ] } });
    });
    let suggestions = 0;
    await page.route(`**/api/inbox/conversations/${original.id}/suggest-reply/`, route => {
      suggestions++;
      return suggestions === 1 ? route.fulfill({ status: 503, json: { detail: "Temporary reply failure" } }) : route.fulfill({ json: { suggested_reply: "Reviewed AI reply" } });
    });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    if (info.project.name === "desktop-chromium") await page.setViewportSize({ width: 1536, height: 695 });
    await page.goto(`/app/conversations/${original.id}`);
    const composer = page.getByTestId("inbox-action-composer");
    await expect(composer).toBeVisible();
    await composer.fill("");
    await page.screenshot({ path: info.outputPath(`compact-initial-${locale}.png`), fullPage: true });
    await info.attach("workspace-geometry", { contentType: "application/json", body: JSON.stringify(await page.evaluate(() => {
      const rect = (selector: string) => {
        const el = document.querySelector(selector);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
      };
      return { viewport: { width: innerWidth, height: innerHeight }, workspace: rect('[data-testid="inbox-workspace-ready"]'), header: rect('[data-testid="inbox-thread-header"]'), composer: rect('[data-testid="inbox-composer"]') };
    })) });
    await composer.fill("Unsent draft");
    const ai = page.getByRole("button", { name: copy["conversations.prepareReply"], exact: true });
    await ai.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("inbox-ai-preview").getByRole("alert")).toBeVisible();
    await expect(composer).toHaveValue("Unsent draft");
    await ai.click();
    const preview = page.getByTestId("inbox-ai-preview");
    await expect(preview.getByText("Reviewed AI reply", { exact: true })).toBeVisible();
    await preview.getByRole("button", { name: copy["common.close"], exact: true }).click();
    await expect(ai).toBeFocused();
    await expect(composer).toHaveValue("Unsent draft");
    await ai.click();
    await preview.getByRole("button", { name: copy["conversations.useSuggestedReply"], exact: true }).click();
    await expect(composer).toHaveValue("Unsent draft\nReviewed AI reply");
    await expect(composer).toBeFocused();
    expect(sends).toBe(0);

    const templates = page.getByRole("button", { name: copy["conversations.quickRepliesButton"], exact: true });
    await templates.click();
    await expect(page.getByRole("dialog", { name: copy["conversations.quickRepliesTitle"], exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(templates).toBeFocused();

    await page.screenshot({ path: info.outputPath(`compact-${locale}.png`), fullPage: true });
    if (info.project.name === "desktop-chromium") {
      // Reflow must retain the draft and keep inspector/actions reachable on laptops.
      for (const width of [1440, 1366, 1024, 768]) {
        await page.setViewportSize({ width, height: 768 });
        const context = page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true });
        if (width < 1440) {
          await expect(context).toHaveAttribute("aria-expanded", "false");
          await context.click();
        } else if (await context.getAttribute("aria-expanded") !== "true") await context.click();
        await expect(page.getByTestId("inbox-customer-context").filter({ visible: true })).toBeVisible();
        if (width < 1440) await page.keyboard.press("Escape");
        await expect(composer).toHaveValue("Unsent draft\nReviewed AI reply");
        await page.screenshot({ path: info.outputPath(`compact-${locale}-${width}.png`), fullPage: true });
      }
    }
    await selectAction(page, copy["conversations.takeDialog"], copy["conversations.dialogActions"]);
    await expect.poll(() => calls.includes("assign")).toBe(true);
    await selectAction(page, copy["conversations.closeDialog"], copy["conversations.dialogActions"]);
    await expect(composer).toBeDisabled();
    await selectAction(page, copy["conversations.openDialog"], copy["conversations.dialogActions"]);
    await expect(composer).toBeEnabled();
    await expect(composer).toHaveValue("Unsent draft\nReviewed AI reply");
    expect(calls).toEqual(["assign", "close", "reopen"]);
    expect(sends).toBe(0);
  });
}
