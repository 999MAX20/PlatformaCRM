import { expect, test, type Page, type Locator } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Client, Lead, Deal, Pipeline, PipelineStage } from "../src/types";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(180_000);
});

async function quick(page: Page, toolbar: Locator, label: string, copy: Record<string, string>) {
  const group = toolbar.getByRole("group", { name: copy["crmFilters.quickFilters"], exact: true });
  const button = group.getByRole("button", { name: new RegExp(`^${label}`) });
  if (await button.isVisible()) await button.click();
  else {
    await group.getByRole("button", { name: copy["crmFilters.moreQuick"], exact: true }).click();
    await page.getByRole("menuitem", { name: new RegExp(`^${label}`) }).click();
  }
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`unified CRM filters: draft, URL, counts, dates and saved view (${locale})`, async ({ page }, info) => {
    const session = await crmSession(page);
    const marker = `Toolbar ${locale} ${info.project.name}`;
    const client = await session.create<Client>("clients", { full_name: marker, source: "manual" });
    await session.create<Lead>("leads", { client: client.id, responsible_user: session.userId, source: "manual", message: marker });
    const pipeline = (await session.list<Pipeline>("pipelines"))[0];
    const stage = (await session.list<PipelineStage>("pipeline-stages")).find(item => item.pipeline === pipeline.id && !item.is_won && !item.is_lost && item.is_active)!;
    await session.create<Deal>("deals", { client: client.id, owner: session.userId, pipeline: pipeline.id, stage: stage.id, title: marker, source: "manual", amount: "12500" });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    const failures: string[] = [];
    page.on("pageerror", error => failures.push(error.message));

    for (const kind of ["clients", "leads", "deals"] as const) {
      await page.goto(`/app/${kind}`);
      const toolbar = page.getByTestId(`${kind}-unified-toolbar`);
      await expect(toolbar).toBeVisible();
      const search = toolbar.getByTestId(`${kind}-search-input`);
      await search.fill(marker);
      await expect(page).toHaveURL(new RegExp("search=Toolbar"));
      await expect.poll(async () => {
        const text = await toolbar.getByRole("group", { name: copy["crmFilters.quickFilters"], exact: true }).innerText();
        return (kind === "clients" ? /\b0\b/ : /\b1\b/).test(text);
      }).toBe(true);
      const applied = page.url();
      const trigger = toolbar.locator(`[data-focus-return-id="${kind}-filters"]`);
      await trigger.click();
      let dialog = page.getByRole("dialog", { name: copy["crmFilters.filters"], exact: true });
      const sources = dialog.getByRole("group", { name: copy["crmFilters.source"], exact: true });
      await sources.locator("summary").click();
      await sources.getByRole("checkbox").nth(1).check();
      await sources.getByRole("checkbox").nth(2).check();
      expect(page.url()).toBe(applied);
      await dialog.getByRole("button", { name: copy["common.cancel"], exact: true }).click();
      await expect(dialog).toBeHidden();
      expect(page.url()).toBe(applied);
      await expect(trigger).toBeFocused();

      await trigger.click();
      dialog = page.getByRole("dialog", { name: copy["crmFilters.filters"], exact: true });
      const dateTrigger = dialog.getByRole("button", { name: new RegExp(`^${copy["crmFilters.created"]}`) });
      await dateTrigger.click();
      const calendar = dialog.getByRole("grid", { name: copy["crmFilters.created"], exact: true });
      await expect(calendar).toBeVisible();
      const year = dialog.getByRole("combobox", { name: copy["crmFilters.year"], exact: true });
      await year.click();
      await page.getByRole("option", { name: "1990", exact: true }).click();
      await expect(year).toContainText("1990");
      await page.screenshot({ path: info.outputPath(`calendar-${kind}-${locale}.png`) });
      await year.click();
      await year.press("Escape");
      await expect(dialog).toBeVisible();
      await expect(calendar).toBeVisible();
      await calendar.getByRole("gridcell").first().focus();
      await page.keyboard.press("ArrowRight");
      await expect(calendar.locator("[tabindex='0']")).toBeFocused();
      await calendar.locator("[tabindex='0']").press("Escape");
      await expect(calendar).toBeHidden();
      await expect(dateTrigger).toBeFocused();
      await dateTrigger.click();
      await dialog.getByRole("button", { name: copy["crmFilters.last7"], exact: true }).click();
      await expect(calendar).toBeHidden();
      await dialog.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
      await expect(page).toHaveURL(/created_from=\d{4}-\d{2}-\d{2}/);
      await expect(toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.remove"]}: ${copy["crmFilters.created"]}`) })).toBeVisible();
      await page.reload();
      await expect(search).toHaveValue(marker);
      await expect(toolbar).toBeVisible();
      await page.screenshot({ path: info.outputPath(`${kind}-${locale}.png`) });
      expect(await toolbar.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);

      if (kind !== "clients") {
        const scope = toolbar.getByRole("combobox", { name: copy["crmFilters.scope"], exact: true });
        await scope.click();
        await page.getByRole("option", { name: copy[`crmFilters.scope.${kind}.mine`], exact: true }).click();
        await expect(page).toHaveURL(/scope=mine/);
        await quick(page, toolbar, copy[kind === "leads" ? "crmFilters.quick.attention" : "crmFilters.quick.no_tasks"], copy);
        await expect(page).toHaveURL(new RegExp(`quick=${kind === "leads" ? "attention" : "no_tasks"}`));
        await expect(scope).toContainText(copy[`crmFilters.scope.${kind}.mine`]);
        await page.goBack();
        await expect(page).not.toHaveURL(/quick=/);
        await expect(scope).toContainText(copy[`crmFilters.scope.${kind}.mine`]);
      }
      await trigger.click();
      dialog = page.getByRole("dialog", { name: copy["crmFilters.filters"], exact: true });
      const presetSection = dialog.locator("details").filter({ has: page.locator("summary", { hasText: copy["crmFilters.savedViews"] }) });
      await presetSection.locator("summary").click();
      await dialog.getByLabel(copy["crmFilters.viewName"], { exact: true }).fill(`${kind} ${locale}`);
      await dialog.getByRole("button", { name: copy["crmFilters.saveView"], exact: true }).click();
      await expect(dialog.getByRole("button", { name: `${kind} ${locale}`, exact: true })).toBeVisible();
      await dialog.getByRole("button", { name: copy["common.reset"], exact: true }).click();
      await dialog.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
      await expect(search).toHaveValue("");
      await expect(page).not.toHaveURL(/created_from=|scope=mine|search=/);
      await trigger.click();
      dialog = page.getByRole("dialog", { name: copy["crmFilters.filters"], exact: true });
      await dialog.locator("summary", { hasText: copy["crmFilters.savedViews"] }).click();
      await dialog.getByRole("button", { name: `${kind} ${locale}`, exact: true }).click();
      await dialog.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
      await expect(search).toHaveValue(marker);
      await expect(page).toHaveURL(/created_from=/);
    }
    expect(failures).toEqual([]);
  });
}

test("advanced combinations, empty reset and failed-count recovery", async ({ page }, info) => {
  await crmSession(page);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "en"));
  const failures: string[] = [];
  page.on("pageerror", error => failures.push(error.message));
  for (const kind of ["clients", "leads", "deals"] as const) {
    await page.goto(`/app/${kind}?created_from=not-a-date`);
    const toolbar = page.getByTestId(`${kind}-unified-toolbar`);
    await expect(toolbar).toBeVisible();
    await expect(page.getByRole("button", { name: en["common.retry"], exact: true })).toBeVisible();
    const group = toolbar.getByRole("group", { name: en["crmFilters.quickFilters"], exact: true });
    expect(await group.locator("button span.tabular-nums").count()).toBe(0);
    const trigger = toolbar.locator(`[data-focus-return-id="${kind}-filters"]`);
    await trigger.click();
    let dialog = page.getByRole("dialog", { name: en["crmFilters.filters"], exact: true });
    await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
    await expect(dialog.getByRole("alert")).toHaveText(en["crmFilters.invalidDate"]);
    await dialog.getByRole("button", { name: en["common.reset"], exact: true }).click();
    const sources = dialog.getByRole("group", { name: en["crmFilters.source"], exact: true });
    await sources.locator("summary").click();
    await sources.getByRole("checkbox").nth(1).check();
    await sources.getByRole("checkbox").nth(2).check();
    await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
    await expect.poll(() => new URL(page.url()).searchParams.get("source")?.split(",").length).toBe(2);
    await expect(page.getByRole("button", { name: en["common.retry"], exact: true })).toBeHidden();
    await trigger.click();
    dialog = page.getByRole("dialog", { name: en["crmFilters.filters"], exact: true });
    await dialog.getByRole("button", { name: en["common.reset"], exact: true }).click();
    await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
    await toolbar.getByTestId(`${kind}-search-input`).fill("no-such-workspace-record-19568322");
    await expect.poll(async () => /\b0\b/.test(await group.innerText())).toBe(true);
    await trigger.click();
    dialog = page.getByRole("dialog", { name: en["crmFilters.filters"], exact: true });
    await dialog.getByRole("button", { name: en["common.reset"], exact: true }).click();
    await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
    await expect(toolbar.getByTestId(`${kind}-search-input`)).toHaveValue("");
  }
  await page.goto("/app/leads?quick=attention&statuses=closed");
  let toolbar = page.getByTestId("leads-unified-toolbar");
  await expect(toolbar).toBeVisible();
  await quick(page, toolbar, en["crmFilters.quick.new"], en);
  await expect(page).not.toHaveURL(/statuses=closed/);
  await expect(page).toHaveURL(/quick=new/);
  await toolbar.locator('[data-focus-return-id="leads-filters"]').click();
  let dialog = page.getByRole("dialog", { name: en["crmFilters.filters"], exact: true });
  const statuses = dialog.getByRole("group", { name: en["crmFilters.statuses"], exact: true });
  await statuses.locator("summary").click();
  await statuses.getByRole("checkbox", { name: en["common.all"], exact: true }).check();
  await statuses.getByRole("checkbox", { name: en["crmFilters.status.closed"], exact: true }).check();
  await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
  await expect(page).toHaveURL(/statuses=closed/);
  await expect(page).not.toHaveURL(/quick=new/);

  await page.goto("/app/deals");
  toolbar = page.getByTestId("deals-unified-toolbar");
  await toolbar.locator('[data-focus-return-id="deals-filters"]').click();
  dialog = page.getByRole("dialog", { name: en["crmFilters.filters"], exact: true });
  const amount = dialog.getByRole("group", { name: en["crmFilters.amount"], exact: true });
  await amount.getByLabel(en["crmFilters.from"], { exact: true }).fill("100");
  await amount.getByLabel(en["crmFilters.to"], { exact: true }).fill("10");
  await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
  await expect(dialog.getByRole("alert")).toHaveText(en["crmFilters.invalidAmount"]);
  await amount.getByLabel(en["crmFilters.to"], { exact: true }).fill("1000");
  await dialog.getByRole("button", { name: new RegExp(`^${en["crmFilters.expected_close"]}`) }).click();
  const calendar = dialog.getByRole("grid", { name: en["crmFilters.expected_close"], exact: true });
  const dates = calendar.getByRole("gridcell");
  const start = await dates.nth(10).getAttribute("data-date");
  const end = await dates.nth(14).getAttribute("data-date");
  await dates.nth(10).click();
  await dates.nth(14).click();
  await dialog.getByRole("button", { name: new RegExp(`^${en["crmFilters.expected_close"]}`) }).click();
  await expect(calendar.locator('[aria-selected="true"]')).toHaveCount(5);
  await page.screenshot({ path: info.outputPath("selected-date-range.png") });
  await dialog.getByRole("button", { name: en["crmFilters.apply"], exact: true }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("expected_close_from")).toBe(start);
  await expect.poll(() => new URL(page.url()).searchParams.get("expected_close_to")).toBe(end);
  expect(failures).toEqual([]);
});
