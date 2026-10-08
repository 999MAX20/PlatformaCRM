import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";
import type { InboxContext, InboxConversation } from "../src/api/inbox";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(150_000);
});

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`client replacement confirms exact links and preserves history (${locale})`, async ({ page }, info) => {
    const session = await crmSession(page);
    const conversation = (await session.list<InboxConversation>("inbox/conversations"))[0];
    const originalName = `Anna Original ${locale}`;
    const replacementName = `Maria Replacement ${locale}`;
    const original = await session.create<{ id: number }>("clients", { full_name: originalName });
    const replacement = await session.create<{ id: number }>("clients", { full_name: replacementName });
    const initialLink = await session.action(`inbox/conversations/${conversation.id}/link-client`, { client_id: original.id });
    if (initialLink.requires_confirmation) await session.action(`inbox/conversations/${conversation.id}/link-client`, { client_id: original.id, confirmation_token: initialLink.confirmation_token });
    await session.action(`inbox/conversations/${conversation.id}/create-deal`, { title: "Original consultation" });
    const context: InboxContext = await session.read(`inbox/conversations/${conversation.id}/context`);
    const messages = await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/conversations/${conversation.id}`);
    const composer = page.getByTestId("inbox-action-composer");
    await composer.fill("Keep this unsent reply");
    const trigger = page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true });
    if (await trigger.getAttribute("aria-expanded") !== "true") await trigger.click();
    const panel = page.getByTestId("inbox-customer-context").filter({ visible: true });
    await panel.getByRole("button", { name: copy["conversations.contextActions"], exact: true }).click();
    await page.getByRole("menuitem", { name: copy["conversations.changeLink.client"], exact: true }).click();
    const picker = page.getByRole("dialog", { name: copy["conversations.linkClientTitle"], exact: true });
    await picker.getByRole("button", { name: replacementName, exact: true }).click();
    const confirmation = page.getByRole("dialog", { name: copy["conversations.clientReplacement.title"], exact: true });
    await expect(confirmation).toContainText(`${originalName} → ${replacementName}`);
    await expect(confirmation.getByRole("button", { name: copy["common.cancel"], exact: true })).toBeFocused();
    await expect(confirmation.getByRole("listitem")).toHaveCount(2);
    await expect(confirmation).toContainText(` ${context.deal.data!.title}`);
    expect((await session.read(`inbox/conversations/${conversation.id}`)).client).toBe(original.id);
    await page.screenshot({ path: info.outputPath(`confirmation-${locale}.png`), fullPage: true });
    await confirmation.getByRole("button", { name: copy["common.cancel"], exact: true }).click();
    await expect(picker).toBeVisible();
    expect((await session.read(`inbox/conversations/${conversation.id}`)).client).toBe(original.id);
    await picker.getByRole("button", { name: replacementName, exact: true }).click();
    if (locale === "ru") {
      // A concurrent relation edit must refresh the actual confirmation list.
      const newLead = await session.create<{ id: number }>("leads", { client: original.id, message: "Updated linked request" });
      await session.action(`inbox/conversations/${conversation.id}/link-lead`, { lead_id: newLead.id });
      await confirmation.getByRole("button", { name: copy["conversations.clientReplacement.confirm"], exact: true }).click();
      await expect(confirmation.getByRole("status")).toContainText(copy["conversations.clientReplacement.refreshed"]);
      await expect(confirmation).toContainText("Updated linked request");
      expect((await session.read(`inbox/conversations/${conversation.id}`)).client).toBe(original.id);
      await page.route(`**/api/inbox/conversations/${conversation.id}/link-client/`, route => route.fulfill({ status: 503, json: { detail: "Temporarily unavailable" } }), { times: 1 });
      await confirmation.getByRole("button", { name: copy["conversations.clientReplacement.confirm"], exact: true }).click();
      await expect(confirmation.getByRole("alert")).toBeVisible();
      expect((await session.read(`inbox/conversations/${conversation.id}`)).client).toBe(original.id);
    }
    const confirmButton = confirmation.getByRole("button", { name: copy["conversations.clientReplacement.confirm"], exact: true });
    if (locale === "en") {
      await confirmButton.focus();
      await page.keyboard.press("Enter");
    } else await confirmButton.click();
    await expect(confirmation).not.toBeVisible();
    const after = await session.read(`inbox/conversations/${conversation.id}`);
    expect(after.client).toBe(replacement.id);
    expect(after.lead).toBeNull();
    expect(after.deal).toBeNull();
    expect((await session.read(`leads/${context.lead.data!.id}`)).client).toBe(original.id);
    expect((await session.read(`deals/${context.deal.data!.id}`)).client).toBe(original.id);
    expect((await session.list<{ id: number }>(`inbox/conversations/${conversation.id}/messages`)).map(row => row.id)).toEqual(messages.map(row => row.id));
    if (info.project.name.includes("mobile")) {
      await panel.getByRole("button", { name: copy["conversations.closeContext"], exact: true }).click();
    }
    await expect(composer).toHaveValue("Keep this unsent reply");
  });
}
