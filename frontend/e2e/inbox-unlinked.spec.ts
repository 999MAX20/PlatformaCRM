import { execFileSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { InboxContext } from "../src/api/inbox";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable runtime required");
  test.setTimeout(120_000);
});

function fixtures(): { create: number; link: number; states: number } {
  return JSON.parse(execFileSync(process.env.E2E_PYTHON!, ["e2e/support/seed-unlinked-clients.py"], { encoding: "utf8", windowsHide: true }).trim().split("\n").at(-1)!);
}

async function inspector(page: Page, copy: Record<string, string>) {
  const trigger = page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true });
  await expect(trigger).toBeVisible();
  const panel = page.getByTestId("inbox-customer-context").filter({ visible: true });
  if (!await panel.isVisible()) {
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await trigger.click();
  }
  await expect(panel).toBeVisible();
  return panel;
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`unlinked client creates, links and opens a task with retained draft ${locale}`, async ({ page }, info) => {
    const ids = fixtures();
    const session = await crmSession(page);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/conversations/${ids.create}`);
    const composer = page.getByTestId("inbox-action-composer");
    await composer.fill("Unsent answer");
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const panel = await inspector(page, copy);
      await expect(panel.getByRole("heading", { name: copy["conversations.clientUnlinked"], exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath(`inbox-${locale}-${width}.png`), fullPage: true });
      if (width < 1440) {
        await panel.getByRole("button", { name: copy["conversations.closeContext"], exact: true }).click();
        await expect(page.getByRole("button", { name: copy["conversations.aboutClient"], exact: true })).toBeFocused();
      }
    }
    let panel = await inspector(page, copy);
    if (locale === "ru") {
      const accessibility = await new AxeBuilder({ page }).include('[data-testid="inbox-customer-context"]').withTags(["wcag2a", "wcag2aa"]).analyze();
      expect(accessibility.violations).toEqual([]);
    }
    const taskButton = panel.getByRole("button", { name: copy["conversations.createTask"], exact: true });
    await taskButton.focus();
    await page.keyboard.press("Enter");
    const task = page.getByRole("dialog", { name: copy["conversations.createTaskTitle"], exact: true });
    await expect(task.getByRole("textbox", { name: copy["taskWorkspace.description"], exact: true })).toHaveValue("Please contact me tomorrow.");
    await page.keyboard.press("Escape");
    await expect(task).toBeHidden();
    await expect(taskButton).toBeFocused();
    await taskButton.click();
    await task.getByLabel(copy["taskWorkspace.name"], { exact: true }).fill(`Unlinked follow-up ${locale}`);
    if (locale === "ru") {
      const taskUrl = `**/api/inbox/conversations/${ids.create}/create-task/`;
      await page.route(taskUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic task outage" } }));
      await task.getByRole("button", { name: copy["tasks.create"], exact: true }).click();
      await expect(task.getByRole("alert")).toBeVisible();
      await expect(task.getByLabel(copy["taskWorkspace.name"], { exact: true })).toHaveValue(`Unlinked follow-up ${locale}`);
      expect((await session.read(`inbox/conversations/${ids.create}/context`)).task).toBeNull();
      await task.getByRole("alert").getByRole("button", { name: copy["common.close"], exact: true }).click();
      await page.unroute(taskUrl);
    }
    const taskSaved = page.waitForResponse(r => r.url().endsWith(`/${ids.create}/create-task/`) && r.request().method() === "POST");
    await task.getByRole("button", { name: copy["tasks.create"], exact: true }).click();
    expect((await taskSaved).ok()).toBe(true);
    await expect(task).toBeHidden();
    panel = await inspector(page, copy);
    let creates = 0;
    page.on("request", r => { if (r.method() === "POST" && r.url().endsWith(`/${ids.create}/create-client/`)) creates++; });
    const created = page.waitForResponse(r => r.url().endsWith(`/${ids.create}/create-client/`) && r.request().method() === "POST");
    await panel.getByRole("button", { name: copy["conversations.createClient"], exact: true }).click();
    expect((await created).ok()).toBe(true);
    await expect(panel.getByTestId("inbox-unlinked-client")).toHaveCount(0);
    const result: InboxContext = await session.read(`inbox/conversations/${ids.create}/context`);
    expect(result.client.data?.id).toBeTruthy();
    expect(result.task?.title).toBe(`Unlinked follow-up ${locale}`);
    expect(creates).toBe(1);
    await panel.getByRole("button", { name: copy["conversations.closeContext"], exact: true }).click();
    await expect(composer).toHaveValue("Unsent answer");

    await page.goto(`/app/conversations/${ids.link}`);
    panel = await inspector(page, copy);
    await panel.getByRole("button", { name: copy["conversations.linkClientAction"], exact: true }).click();
    const picker = page.getByRole("dialog", { name: copy["conversations.linkClientTitle"], exact: true });
    await picker.getByPlaceholder(copy["conversations.linkSearchPlaceholder"]).fill(result.client.data!.name);
    const linked = page.waitForResponse(r => r.url().endsWith(`/${ids.link}/link-client/`) && r.request().method() === "POST");
    await picker.getByRole("button").filter({ hasText: result.client.data!.name }).click();
    expect((await linked).ok()).toBe(true);
    await expect(picker).toBeHidden();
    const linkResult: InboxContext = await session.read(`inbox/conversations/${ids.link}/context`);
    expect(linkResult.client.data?.id).toBe(result.client.data!.id);
  });
}

test("unlinked inspector recovers from context/create errors and respects unavailable actions", async ({ page }) => {
  const ids = fixtures();
  const session = await crmSession(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  const contextUrl = `**/api/inbox/conversations/${ids.states}/context/`;
  await page.route(contextUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic context outage" } }));
  await page.goto(`/app/conversations/${ids.states}`);
  let panel = await inspector(page, ru);
  await expect(panel.getByRole("button", { name: ru["common.retry"], exact: true })).toBeVisible();
  await page.unroute(contextUrl);
  await panel.getByRole("button", { name: ru["common.retry"], exact: true }).click();
  const create = panel.getByRole("button", { name: ru["conversations.createClient"], exact: true });
  await expect(create).toBeVisible();
  const createUrl = `**/api/inbox/conversations/${ids.states}/create-client/`;
  await page.route(createUrl, route => route.fulfill({ status: 503, json: { detail: "Synthetic create outage" } }));
  await create.click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(create).toBeEnabled();
  expect((await session.read(`inbox/conversations/${ids.states}/context`)).client.data).toBeNull();
  await page.unroute(createUrl);
  await create.click();
  await expect(panel.getByTestId("inbox-unlinked-client")).toHaveCount(0);

  const actual: InboxContext = await session.read(`inbox/conversations/${ids.link}/context`);
  await page.route(`**/api/inbox/conversations/${ids.link}/context/`, route => route.fulfill({ json: {
    ...actual, client: { state: "empty", data: null },
    actions: Object.fromEntries(Object.keys(actual.actions).map(key => [key, false])),
  } }));
  await page.goto(`/app/conversations/${ids.link}`);
  panel = await inspector(page, ru);
  await expect(panel.getByRole("heading", { name: ru["conversations.clientUnlinked"], exact: true })).toBeVisible();
  await expect(panel.getByRole("button", { name: ru["conversations.createClient"], exact: true })).toHaveCount(0);
  await expect(panel.getByRole("button", { name: ru["conversations.linkClientAction"], exact: true })).toHaveCount(0);
  await expect(panel.getByRole("button", { name: ru["conversations.createTask"], exact: true })).toHaveCount(0);
});
