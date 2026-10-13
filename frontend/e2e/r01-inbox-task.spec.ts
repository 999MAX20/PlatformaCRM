import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { InboxConversation, InboxContext } from "../src/api/inbox";
import type { Task } from "../src/types";

test.use({ timezoneId: "UTC", actionTimeout: 15_000 });
test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

async function openTask(page: Page, copy: Record<string, string>) {
  const menu = page.getByRole("button", { name: copy["conversations.dialogActions"], exact: true });
  await menu.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("menuitem", { name: copy["conversations.createTask"], exact: true }).click();
  return page.getByRole("dialog", { name: copy["conversations.createTaskTitle"], exact: true });
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`R01 Inbox deadline persists in business time when browser is UTC ${locale}`, async ({ page }) => {
    const s = await crmSession(page);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const conversation = (await s.list<InboxConversation>("inbox/conversations"))[0];
    const context: InboxContext = await s.read(`inbox/conversations/${conversation.id}/context`);
    expect(context.timezone).not.toBe("UTC");
    await page.goto(`/app/conversations/${conversation.id}`);
    let dialog = await openTask(page, copy);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page.getByRole("button", { name: copy["conversations.dialogActions"], exact: true })).toBeFocused();
    dialog = await openTask(page, copy);
    await dialog.getByLabel(copy["tasks.dueAt"], { exact: true }).fill("2030-10-15T10:30");
    const saved = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith(`/inbox/conversations/${conversation.id}/create-task/`));
    await dialog.getByRole("button", { name: copy["tasks.create"], exact: true }).click();
    const response = await saved;
    expect(response.ok()).toBeTruthy();
    const task: Task = await s.read(`tasks/${(await response.json()).id}`);
    const parts = new Intl.DateTimeFormat("en-CA", { timeZone: context.timezone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(task.due_at!));
    const part = (key: string) => parts.find(p => p.type === key)!.value;
    expect(`${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`).toBe("2030-10-15T10:30");
  });

  test(`R01 Inbox lost response retry creates one task and a new intent stays distinct ${locale}`, async ({ page }) => {
    const s = await crmSession(page);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const conversation = (await s.list<InboxConversation>("inbox/conversations"))[0];
    const title = `R01 retry ${Date.now()}`;
    await page.goto(`/app/conversations/${conversation.id}`);
    const dialog = await openTask(page, copy);
    await dialog.getByLabel(copy["taskWorkspace.name"], { exact: true }).fill(title);
    let committedId: number | undefined;
    let committedKey: string | undefined;
    await page.route(`**/api/inbox/conversations/${conversation.id}/create-task/`, async route => {
      committedKey = route.request().headers()["idempotency-key"];
      const committed = await route.fetch();
      expect(committed.ok()).toBeTruthy();
      committedId = (await committed.json()).id;
      await route.fulfill({ status: 503, json: { detail: "Response lost after commit" } });
    }, { times: 1 });
    const submit = dialog.getByRole("button", { name: copy["tasks.create"], exact: true });
    await submit.click();
    await expect(page.getByRole("alert").first()).toBeVisible();
    await expect(dialog.getByLabel(copy["taskWorkspace.name"], { exact: true })).toHaveValue(title);
    expect(committedId).toBeTruthy();
    const retried = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith(`/inbox/conversations/${conversation.id}/create-task/`));
    await submit.click();
    const response = await retried;
    expect(response.ok()).toBeTruthy();
    expect(committedKey).toBeTruthy();
    expect(response.request().headers()["idempotency-key"]).toBe(committedKey);
    expect((await response.json()).id).toBe(committedId);
    await expect(dialog).toBeHidden();
    expect((await s.list<Task>("tasks")).filter(task => task.title === title)).toHaveLength(1);
    const history = await s.read("activity-events", { entity_type: "Task", entity_id: committedId! });
    expect(history.results.filter((event: { event_type: string }) => event.event_type === "task_created")).toHaveLength(1);
    const next = await openTask(page, copy);
    await next.getByLabel(copy["taskWorkspace.name"], { exact: true }).fill(title);
    const created = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith(`/inbox/conversations/${conversation.id}/create-task/`));
    await next.getByRole("button", { name: copy["tasks.create"], exact: true }).click();
    const nextResponse = await created;
    expect(nextResponse.request().headers()["idempotency-key"]).not.toBe(committedKey);
    expect((await nextResponse.json()).id).not.toBe(committedId);
    expect((await s.list<Task>("tasks")).filter(task => task.title === title)).toHaveLength(2);
  });

}
