import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required");
  test.setTimeout(180_000);
});

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`seven client filters: draft, URL, calendar, empty and recovery (${locale})`, async ({ page }, info) => {
    const session = await crmSession(page);
    const marker = `Filter acceptance ${locale} ${info.project.name} ${Date.now()}`;
    const record = await session.create<{ id: number }>("clients", { full_name: marker, source: "manual" });
    const tag = await session.create<{ id: number }>("tags", { name: marker });
    await session.create("tagged-objects", { tag: tag.id, entity_type: "client", entity_id: String(record.id) });
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/clients?search=${encodeURIComponent(marker)}&segment=999999&handoff=true&custom_field=999999&custom_value=hidden`);
    const toolbar = page.getByTestId("clients-unified-toolbar");
    const trigger = toolbar.locator('[data-focus-return-id="clients-filters"]');
    const panel = page.getByTestId("clients-filters-panel");
    const list = page.getByTestId("clients-workspace-ready");
    const client = list.getByText(marker, { exact: true }).filter({ visible: true });
    await expect(client).toBeVisible();
    await expect(toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.quick.no_reply"]}`) })).toBeVisible();
    await trigger.press("Enter");
    for (const key of ["added", "source", "tag", "appointment", "task", "contact", "archive"]) {
      await expect(panel.getByText(copy[`crmFilters.${key}`], { exact: true })).toBeVisible();
    }
    for (const key of ["segment", "handoff", "savedViews"]) await expect(panel.getByText(copy[`crmFilters.${key}`], { exact: true })).toHaveCount(0);
    await panel.getByRole("combobox", { name: new RegExp(`^${copy["crmFilters.contact"]}`) }).click();
    await panel.getByRole("option", { name: copy["crmFilters.contact.missing_phone"], exact: true }).click();
    await panel.getByRole("button", { name: copy["common.cancel"], exact: true }).click();
    await expect(trigger).toBeFocused();
    await expect(page).not.toHaveURL(/contact=/);
    await trigger.click();
    for (const [key, value] of [["contact", "missing_email"], ["task", "no_open"], ["appointment", "no_upcoming"]]) {
      await panel.getByRole("combobox", { name: new RegExp(`^${copy[`crmFilters.${key}`]}`) }).click();
      await panel.getByRole("option", { name: copy[`crmFilters.${key}.${value}`], exact: true }).click();
    }
    await page.screenshot({ path: info.outputPath(`filters-${locale}.png`) });
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).toHaveURL(/contact=missing_email/);
    await expect(page).not.toHaveURL(/segment=|handoff=|custom_field=/);
    await expect(client).toBeVisible();
    await page.reload();
    await expect(toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.remove"]}: ${copy["crmFilters.task"]}`) })).toBeVisible();
    await trigger.click();
    await panel.getByRole("combobox", { name: new RegExp(`^${copy["crmFilters.appointment"]}`) }).click();
    await panel.getByRole("option", { name: copy["crmFilters.appointment.period"], exact: true }).click();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(panel.getByRole("alert")).toHaveText(copy["crmFilters.appointmentDateRequired"]);
    await panel.getByRole("button", { name: new RegExp(`^${copy["crmFilters.appointmentDates"]}`) }).click();
    const calendar = page.getByRole("dialog", { name: copy["crmFilters.appointmentDates"], exact: true });
    await calendar.getByRole("gridcell").nth(10).click();
    await calendar.getByRole("gridcell").nth(13).click();
    await calendar.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(panel).toBeVisible();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).toHaveURL(/appointment_from=/);
    await expect(client).toHaveCount(0);
    await expect(list).toHaveAttribute("aria-busy", "false");
    await toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.remove"]}: ${copy["crmFilters.appointment"]}`) }).click();
    await expect(client).toBeVisible();
    await page.route("**/api/clients/?**", route => route.fulfill({ status: 503, json: { detail: "Isolated read failure" } }));
    await toolbar.getByTestId("clients-search-input").fill(`${marker} failure`);
    await expect(page.getByRole("button", { name: copy["common.retry"], exact: true })).toBeVisible({ timeout: 30_000 });
    await page.unroute("**/api/clients/?**");
    await toolbar.getByTestId("clients-search-input").fill(marker);
    await expect(client).toBeVisible();
    await trigger.click();
    await panel.getByRole("button", { name: copy["common.reset"], exact: true }).click();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).not.toHaveURL(/contact=|task=|appointment=|search=/);
    await toolbar.getByTestId("clients-search-input").fill(marker);
    await trigger.click();
    const sources = panel.getByRole("group", { name: copy["crmFilters.source"], exact: true });
    await sources.locator("summary").click();
    await sources.getByRole("checkbox", { name: copy["clients.sourceManual"], exact: true }).check();
    const tags = panel.getByRole("group", { name: copy["crmFilters.tag"], exact: true });
    await tags.locator("summary").click();
    await tags.getByRole("checkbox", { name: marker, exact: true }).check();
    await panel.getByRole("button", { name: new RegExp(`^${copy["crmFilters.added"]}`) }).click();
    const addedCalendar = page.getByRole("dialog", { name: copy["crmFilters.added"], exact: true });
    await addedCalendar.getByRole("button", { name: copy["crmFilters.today"], exact: true }).click();
    await addedCalendar.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(client).toBeVisible();
    await expect(page).toHaveURL(/source=manual/);
    await expect(page).toHaveURL(new RegExp(`tag=${tag.id}`));
    await expect(page).toHaveURL(/created_from=/);
    await trigger.click();
    await panel.getByRole("combobox", { name: new RegExp(`^${copy["crmFilters.archive"]}`) }).click();
    await panel.getByRole("option", { name: copy["crmFilters.archive.archived"], exact: true }).click();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(client).toHaveCount(0);
    await toolbar.getByRole("button", { name: copy["common.reset"], exact: true }).click();
    await expect(page).not.toHaveURL(/archive=|tag=|source=|created_from=/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("shared calendar still applies the appointments period", async ({ page }) => {
  await crmSession(page);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.goto("/app/appointments?from=2026-11-04&to=2026-11-04");
  await page.locator('[data-focus-return-id="records-period"]').click();
  const calendar = page.locator("#records-period-panel");
  await calendar.locator('[data-date="2026-11-05"]').click();
  await calendar.locator('[data-date="2026-11-06"]').click();
  await calendar.getByRole("button", { name: ru["crmFilters.apply"], exact: true }).click();
  await expect(page).toHaveURL(/from=2026-11-05/);
  await expect(page).toHaveURL(/to=2026-11-06/);
});
