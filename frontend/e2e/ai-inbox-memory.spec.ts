import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test("Inbox memory reset requires confirmation and preserves message history", async ({ page }, info) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated synthetic fixtures");
  const session = await crmSession(page);
  const conversations = await session.list<{ id: number }>("inbox/conversations");
  expect(conversations.length).toBeGreaterThan(0);
  const id = conversations[0].id;
  const before = await session.list<{ id: number }>(`inbox/conversations/${id}/messages`);
  expect(before.length).toBeGreaterThan(0);
  await page.goto(`/app/conversations?conversation=${id}`);
  await page.getByRole("button", { name: "Очистить память", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Очистить память", exact: true });
  await dialog.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "Очистить память", exact: true }).click();
  const response = page.waitForResponse(item => item.url().endsWith(`/inbox/conversations/${id}/reset-ai-memory/`) && item.request().method() === "POST");
  await dialog.getByRole("button", { name: "Очистить память", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.getByRole("status").filter({ hasText: "Память очищена. История диалога сохранена." })).toBeVisible();
  const after = await session.list<{ id: number }>(`inbox/conversations/${id}/messages`);
  expect(after.map(item => item.id)).toEqual(before.map(item => item.id));
  await page.screenshot({ path: info.outputPath("inbox-memory-reset.png"), fullPage: true });
});
