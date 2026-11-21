import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required"); test.setTimeout(180_000); });

async function fixture(page: Page, day: string) {
  const s = await crmSession(page);
  const stamp = Date.now();
  const branch = await s.create<{ id: number }>("branches", { name: `QA rooms ${stamp}`, address: "Test address" });
  const staff = await s.create<{ id: number; name: string }>("resources", { name: `Specialist ${stamp}`, resource_type: "staff" });
  const rooms = [];
  const serviceIds: number[] = [];
  const visits: number[] = [];
  const client = await s.create<{ id: number }>("clients", { full_name: `QA client ${stamp}` });
  for (let index = 0; index < 2; index++) {
    const room = await s.create<{ id: number; name: string }>("resources", { name: `Room ${index} ${stamp}`, resource_type: index ? "equipment" : "room", branch: branch.id });
    rooms.push(room);
    const service = await s.create<{ id: number }>("services", { name: `Service ${index} ${stamp}`, duration_minutes: 30 });
    serviceIds.push(service.id);
    await s.action(`branches/${branch.id}/offers`, { service: service.id, duration_minutes: 30, price_from: "0" });
    await s.action(`branches/${branch.id}/assignments`, { resource: staff.id, service_ids: serviceIds });
    for (const resource of [null, staff.id]) await s.action(`branches/${branch.id}/schedule`, { resource, date: day, intervals: [{ start: "09:00", end: "18:00" }] });
    await s.action(`branches/${branch.id}/resource-requirements`, { service: service.id, resource_ids: [room.id] });
    const slots = await s.read("appointments/available-slots", { business_id: s.business, branch_id: branch.id, resource_id: staff.id, service_id: service.id, date: day });
    for (const slot of slots.filter((_: unknown, index: number) => index % 2 === 0).slice(0, 3)) {
      const visit = await s.create<{ id: number }>("appointments", { client: client.id, branch: branch.id, service: service.id, resource: staff.id, start_at: slot.start_at });
      visits.push(visit.id);
    }
  }
  return { ...s, branch, staff, rooms, visits };
}

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`physical resource link and independent filter reset ${locale}`, async ({ page }, info) => {
    const day = `2030-01-${String(7 + ["ru", "kk", "en"].indexOf(locale) + (info.project.name.startsWith("mobile") ? 3 : 0)).padStart(2, "0")}`;
    const s = await fixture(page, day);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/business/resources?branch=${s.branch.id}`);
    await page.getByLabel(`${copy["management.actions"]}: ${s.rooms[0].name}`, { exact: true }).click();
    const related = page.getByRole("link", { name: copy["management.appointments"], exact: true });
    await expect(related).toHaveAttribute("href", `/app/appointments?physical_resource=${s.rooms[0].id}&branch=${s.branch.id}`);
    await related.click();
    await expect(page.getByTestId("records-workspace")).toBeVisible();
    const rows = page.locator(`[aria-label^="${copy["appointments.card"]} #"]:visible`);
    await expect(rows).toHaveCount(3);
    // API and visible list must agree on the room's three visits across all dates.
    await expect.poll(async () => (await s.read("appointments/workspace", { business: s.business, physical_resource: s.rooms[0].id })).count).toBe(3);
    const path = `/app/appointments?physical_resource=${s.rooms[0].id}&resource=${s.staff.id}&branch=${s.branch.id}&from=${day}&to=${day}`;
    await page.goto(path);
    await expect(rows).toHaveCount(3);
    const trigger = page.getByTestId("records-toolbar").getByRole("button", { name: new RegExp(`^${copy["crmFilters.filters"]}`) });
    const panel = page.getByRole("dialog", { name: copy["crmFilters.filters"], exact: true });
    const open = async () => { await trigger.click(); await expect(panel).toBeVisible(); };
    const choose = async (label: string, option: string) => {
      await panel.getByRole("combobox", { name: new RegExp(`^${label}`) }).click();
      await page.getByRole("option", { name: option, exact: true }).click();
    };
    await open();
    await expect(panel.getByRole("combobox", { name: new RegExp(`^${copy["records.physicalResource"]}`) })).toContainText(s.rooms[0].name);
    await panel.getByRole("combobox", { name: new RegExp(`^${copy["records.specialist"]}`) }).click();
    await expect(page.getByRole("option", { name: s.rooms[0].name, exact: true })).toHaveCount(0);
    await page.keyboard.press("Escape");
    await page.screenshot({ path: info.outputPath(`physical-filter-${locale}.png`), fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await panel.getByRole("button", { name: copy["common.reset"], exact: true }).click();
    await panel.getByRole("button", { name: copy["common.cancel"], exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`physical_resource=${s.rooms[0].id}`));
    await expect(trigger).toBeFocused();
    await open();
    await choose(copy["records.physicalResource"], s.rooms[1].name);
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`physical_resource=${s.rooms[1].id}`));
    await expect(rows).toHaveCount(3);
    await page.reload();
    await open();
    await expect(panel.getByRole("combobox", { name: new RegExp(`^${copy["records.physicalResource"]}`) })).toContainText(s.rooms[1].name);
    await choose(copy["records.physicalResource"], copy["records.all"]);
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    let params = new URL(page.url()).searchParams;
    expect(params.has("physical_resource")).toBe(false);
    expect(params.get("resource")).toBe(String(s.staff.id));
    expect(params.get("from")).toBe(day);
    await expect(rows).toHaveCount(6);
    await page.goBack();
    await expect(page).toHaveURL(new RegExp(`physical_resource=${s.rooms[1].id}`));
    await page.goForward();
    await open();
    await panel.getByRole("button", { name: copy["common.reset"], exact: true }).click();
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    params = new URL(page.url()).searchParams;
    for (const key of ["physical_resource", "resource", "branch"]) expect(params.has(key)).toBe(false);
    expect(params.get("from")).toBe(day);
    expect(params.get("to")).toBe(day);
    await expect(page.getByTestId("records-workspace")).toHaveAttribute("aria-busy", "false");
    await expect(rows).toHaveCount(6);
    await page.screenshot({ path: info.outputPath(`reset-period-${locale}.png`), fullPage: true });
    await page.goto(`/app/appointments?physical_resource=9223372036854775807&from=${day}&to=${day}`);
    await expect(page.getByTestId("records-workspace")).toHaveAttribute("aria-busy", "false");
    await expect(rows).toHaveCount(0);
    await expect(trigger).toBeVisible();
    await expect(page.getByRole("button", { name: copy["records.resetToday"], exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`empty-filter-${locale}.png`), fullPage: true });
    if (locale === "ru") {
      await page.route("**/api/appointments/workspace/**", route => route.fulfill({ status: 503, json: { detail: "Temporary test outage" } }));
      await page.goto(path);
      await expect(page.getByText(copy["records.loadFailed"], { exact: true })).toBeVisible();
      await page.unroute("**/api/appointments/workspace/**");
      await page.getByRole("button", { name: copy["common.retry"], exact: true }).click();
      await expect(rows).toHaveCount(3);
      expect(new URL(page.url()).searchParams.get("physical_resource")).toBe(String(s.rooms[0].id));
    }
  });
}
