import { expect, test, type Page } from "@playwright/test";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.E2E_HANDOFF_RECOVERY !== "1", "Use scripts/verify_handoff_recovery.py for disposable fixtures");
  test.setTimeout(120_000);
});

function fixture(code: string) {
  expect(process.env.ZANI_QUALITY_GATE).toBe("1");
  expect(process.env.DATABASE_URL).toContain("zani-quality-gate-");
  const result = spawnSync(process.env.E2E_PYTHON!, ["manage.py", "shell", "-c", `
import os, json
assert os.environ.get('ZANI_QUALITY_GATE') == '1'
assert 'zani-quality-gate-' in os.environ['DATABASE_URL']
${code}
`], { cwd: path.resolve(process.cwd(), ".."), env: process.env, encoding: "utf8", timeout: 30_000 });
  expect(result.status, result.stderr || String(result.error || "")).toBe(0);
  return JSON.parse(result.stdout.trim().split("\n").at(-1)!);
}

async function ordinaryDialog(page: Page) {
  const session = await crmSession(page);
  const { id } = fixture(`
from apps.businesses.models import Business
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.bots.inbox_service import register_bot_message
business = Business.objects.get(pk=${Number(session.business)})
BotConversation.objects.filter(business=business, bot__name='Idle return fixture').update(ai_resume_at=None, handoff_resume_started_at=None, ai_resume_actor=None)
bot = Bot.objects.create(business=business, name='Idle return fixture', status='active', settings_json={'auto_crm_pipeline': {'mode': 'triage', 'enabled': True, 'auto_send_reply': True}})
AgentProfile.objects.create(business=business, bot=bot, name='Idle return fixture')
BusinessKnowledgeItem.objects.create(business=business, bot=bot, title='Hours', content='Open daily', customer_visible=True)
BotChannel.objects.create(bot=bot, channel='website', status='active')
conversation = BotConversation.objects.create(business=business, bot=bot, channel='website', external_user_id='idle-return-fixture')
message = BotMessage.objects.create(conversation=conversation, direction='inbound', sender_type='client', text='Can a staff member help?')
register_bot_message(message)
print(json.dumps({'id': conversation.pk}))
`) as { id: number };
  await page.goto(`/app/conversations?conversation=${id}`);
  const menu = page.getByRole("button", { name: ru["conversations.dialogActions"], exact: true });
  await menu.click();
  await page.getByRole("menuitem", { name: ru["conversations.handoffToManager"], exact: true }).click();
  await expect(page.getByTestId("inbox-ai-return")).toHaveText(ru["conversations.aiReturnWaiting"]);
  await page.getByTestId("inbox-action-composer").fill("Staff answered the question");
  await page.getByTestId("inbox-action-send").click();
  await expect(page.getByTestId("inbox-action-composer")).toHaveValue("");
  const messages = await session.read(`inbox/conversations/${id}/messages`);
  const reply = messages.results.find((message: { sender_type: string }) => message.sender_type === "manager");
  // The isolated website provider is deliberately mocked, so it must not arm a timer.
  expect(reply.status).toBe("failed");
  expect((await session.read(`inbox/conversations/${id}`)).ai_resume_at).toBeNull();
  fixture(`
from unittest.mock import patch
from apps.bots.models import BotMessage
from apps.bots.outbound_delivery import retry_outbound_message
message = BotMessage.objects.get(pk=${Number(reply.id)})
with patch('apps.bots.outbound_delivery.send_message', return_value={'ok': True}):
    retry_outbound_message(message, actor=message.conversation.business.owner)
print(json.dumps({'ok': True}))
`);
  expect((await session.read(`inbox/conversations/${id}`)).ai_resume_at).toBeTruthy();
  await page.reload();
  await expect(page.getByTestId("inbox-ai-return")).toContainText("Возврат к ИИ после");
  return { ...session, id };
}

test("answered handoff exposes deadline in each locale and preserves it after failed manual stop", async ({ page }, info) => {
  const session = await ordinaryDialog(page);
  for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.reload();
    const notice = page.getByTestId("inbox-ai-return");
    await expect(notice).toContainText(copy["conversations.aiReturnsAfter"].split("{time}")[0]);
    const menu = page.getByRole("button", { name: copy["conversations.dialogActions"], exact: true });
    await menu.focus();
    await menu.press("Enter");
    await expect(page.getByRole("menuitem", { name: copy["conversations.keepAiPaused"], exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(menu).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    await page.screenshot({ path: info.outputPath(`ai-return-${language}.png`), fullPage: true });
  }
  await page.route(`**/api/inbox/conversations/${session.id}/ai-state/`, route => {
    if (route.request().method() !== "POST") return route.continue();
    return route.fulfill({ status: 503, headers: { "Access-Control-Allow-Origin": new URL(page.url()).origin,
      "Access-Control-Allow-Credentials": "true" }, json: { detail: "Synthetic unavailable" } });
  });
  const menu = page.getByRole("button", { name: en["conversations.dialogActions"], exact: true });
  await menu.click();
  await page.getByRole("menuitem", { name: en["conversations.keepAiPaused"], exact: true }).click();
  await expect(page.getByText(en["actions.errorTemporary"], { exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("inbox-ai-return")).toBeVisible();
  expect((await session.read(`inbox/conversations/${session.id}`)).ai_resume_at).toBeTruthy();
  await page.unroute(`**/api/inbox/conversations/${session.id}/ai-state/`);
  await menu.click();
  await page.getByRole("menuitem", { name: en["conversations.keepAiPaused"], exact: true }).click();
  await expect(page.getByTestId("inbox-ai-return")).toHaveCount(0);
  const current = await session.read(`inbox/conversations/${session.id}`);
  expect(current.bot_enabled).toBe(false);
  expect(current.ai_resume_at).toBeNull();
  expect(current.handoff_resume_started_at).toBeNull();
});

test("scheduled task returns answered dialog to AI without sending a message", async ({ page }) => {
  const session = await ordinaryDialog(page);
  const before = await session.read(`inbox/conversations/${session.id}/messages`);
  const result = fixture(`
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from apps.bots.tasks import resume_answered_handoffs_task
now = timezone.now() + timedelta(hours=1, minutes=1)
with patch('django.utils.timezone.now', return_value=now):
    first = resume_answered_handoffs_task.run()
    second = resume_answered_handoffs_task.run()
print(json.dumps({'first': first, 'second': second}))
`);
  expect(result).toEqual({ first: { resumed: 1 }, second: { resumed: 0 } });
  await page.reload();
  await expect(page.getByTestId("inbox-ai-return")).toHaveCount(0);
  await expect(page.getByTestId("inbox-thread-header")).toContainText(ru["conversations.botActive"]);
  expect((await session.read(`inbox/conversations/${session.id}`)).handoff_required).toBe(false);
  expect((await session.read(`inbox/conversations/${session.id}/messages`)).count).toBe(before.count);
});
