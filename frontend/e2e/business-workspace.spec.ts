import { readFileSync } from "node:fs";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { Branch, BranchConfiguration } from "../src/api/branches";
import type { Resource, Service } from "../src/types";

type Fixture = { email: string; business: number; branch: number; second: number; staff: number; room: number; service: number; member: number; manager_email: string };
const fixtures: Record<string, Fixture> = process.env.BUSINESS_WORKSPACE_FIXTURE ? JSON.parse(readFileSync(process.env.BUSINESS_WORKSPACE_FIXTURE, "utf8")) : {};
test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1" || !process.env.BUSINESS_WORKSPACE_FIXTURE, "Requires scripts/verify_business_workspace.py disposable fixtures"); });

async function choose(page: Page, label: string, value: string, within: Page | Locator = page) {
  await within.getByRole("combobox", { name: new RegExp(`^${label} `) }).click();
  await page.getByRole("option", { name: value, exact: true }).click();
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}
function nav(page: Page, dictionary: Record<string, string> = ru) {
  return page.getByRole("navigation", { name: dictionary["business.navigationLabel"], exact: true });
}

test("single location company draft, real profile synchronization and physical resource creation", async ({ page }, info) => {
  const f = fixtures.single;
  const session = await crmSession(page, f.email);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/app/business");
  await expect(page).toHaveURL(/business\/company/);
  await expect(nav(page).getByRole("link")).toHaveCount(6);
  const name = page.getByLabel(ru["businessForm.name"], { exact: true });
  await name.fill("Updated workspace");
  await nav(page).getByRole("link", { name: ru["branches.title"], exact: true }).click();
  const confirm = page.getByRole("dialog", { name: ru["taskWorkspace.discardTitle"], exact: true });
  await expect(confirm).toBeVisible();
  await confirm.getByRole("button", { name: ru["taskWorkspace.keepEditing"], exact: true }).click();
  await expect(name).toHaveValue("Updated workspace");
  await page.getByRole("button", { name: ru["businessForm.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`businesses/${f.business}`)).name).toBe("Updated workspace");
  await nav(page).getByRole("link", { name: ru["branches.title"], exact: true }).click();
  await expect(page.getByTestId("automatic-location")).toContainText("Updated workspace");
  await page.screenshot({ path: info.outputPath("single-desktop.png"), fullPage: true });
  await nav(page).getByRole("link", { name: ru["branches.physicalResources"], exact: true }).click();
  await expect(page.getByTestId("resource-row").filter({ visible: true })).toHaveCount(1);
  await page.getByRole("button", { name: ru["resources.add"], exact: true }).click();
  const create = page.getByRole("dialog", { name: ru["resources.add"], exact: true });
  await create.getByLabel(ru["resources.name"], { exact: true }).fill("Scanner single");
  await choose(page, ru["resources.type"], ru["resources.typeEquipment"], create);
  await create.getByRole("button", { name: ru["resources.save"], exact: true }).click();
  await expect(create).not.toBeVisible();
  await expect.poll(async () => (await session.list<Resource>("resources")).some(item => item.name === "Scanner single" && item.resource_type === "equipment")).toBe(true);
  await expect(page.getByRole("dialog", { name: "Scanner single", exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await noOverflow(page);
});

test("network service conditions, requirements, staff assignment and independent CRM access", async ({ page }, info) => {
  const f = fixtures.network;
  const session = await crmSession(page, f.email);
  await page.goto(`/app/business/services?branch=${f.second}&service=${f.service}`);
  const dialog = page.getByRole("dialog", { name: "Consultation", exact: true });
  await expect(dialog).toBeVisible();
  const terms = dialog.locator("form").filter({ has: page.getByRole("heading", { name: ru["business.branchTerms"], exact: true }) });
  await terms.getByLabel(ru["branches.price"], { exact: true }).fill("0");
  await terms.getByLabel(ru["branches.duration"], { exact: true }).fill("60");
  await page.route(`**/api/branches/${f.second}/offers/`, route => route.fulfill({ status: 503, json: { detail: "Temporary test outage" } }), { times: 1 });
  await terms.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(terms.getByRole("alert")).toBeVisible();
  await expect(terms.getByLabel(ru["branches.price"], { exact: true })).toHaveValue("0");
  await terms.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`branches/${f.second}/configuration`) as BranchConfiguration).offers.find(item => item.service === f.service)?.price_from).toBe("0.00");
  await dialog.getByRole("checkbox", { name: "North room", exact: true }).check();
  await dialog.getByRole("button", { name: ru["branches.saveRequirements"], exact: true }).click();
  await expect.poll(async () => (await session.read(`branches/${f.second}/configuration`) as BranchConfiguration).resource_requirements.length).toBe(1);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await nav(page).getByRole("link", { name: ru["business.staff"], exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`staff\\?branch=${f.second}$`));
  await page.getByTestId("resource-row").filter({ visible: true }).filter({ hasText: "Anna" }).click();
  const staff = page.getByRole("dialog", { name: "Anna", exact: true });
  await expect(staff.getByRole("heading", { name: ru["business.assignments"], exact: true })).toBeVisible();
  const assignment = staff.locator("section").filter({ has: page.getByRole("heading", { name: ru["business.assignments"], exact: true }) });
  await assignment.getByRole("checkbox", { name: ru["branches.active"], exact: true }).uncheck();
  await assignment.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`branches/${f.second}/configuration`) as BranchConfiguration).assignments.find(row => row.resource === f.staff)?.is_active).toBe(false);
  await assignment.getByRole("checkbox", { name: ru["branches.active"], exact: true }).check();
  await assignment.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect.poll(async () => (await session.read(`branches/${f.second}/configuration`) as BranchConfiguration).assignments.find(row => row.resource === f.staff)?.is_active).toBe(true);
  await staff.getByTestId("team-access-toggle").click();
  const confirmation = page.getByRole("dialog", { name: ru["teamAccess.disable"], exact: true });
  await confirmation.getByRole("button", { name: ru["teamAccess.disable"], exact: true }).click();
  await expect.poll(async () => (await session.read(`team/members/${f.member}`)).is_active).toBe(false);
  expect((await session.read(`resources/${f.staff}`)).is_active).toBe(true);
  await page.screenshot({ path: info.outputPath("staff-access.png"), fullPage: true });
});

test("network weekly template, date override reset, conflict recovery and today", async ({ page }, info) => {
  const f = fixtures.recovery;
  const session = await crmSession(page, f.email);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/app/business/working-hours?branch=${f.second}&date=2030-01-07`);
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByRole("button", { name: ru["business.weekTemplate"], exact: true }).click();
  const modal = page.getByRole("dialog");
  await modal.getByLabel(ru["branches.start"], { exact: true }).fill("14:00");
  await modal.getByLabel(ru["branches.end"], { exact: true }).fill("17:00");
  await modal.getByRole("checkbox", { name: ru["weekday.tueShort"], exact: true }).check();
  await modal.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(modal).not.toBeVisible();
  const config = await session.read(`branches/${f.second}/configuration`) as BranchConfiguration;
  for (const weekday of [0, 1]) expect(config.days.find(day => day.resource === f.staff && day.weekday === weekday && !day.date)?.intervals).toEqual([{ start: "14:00", end: "17:00" }]);
  const monday = page.getByRole("table").getByRole("button", { name: /Anna, .*14:00–17:00/ }).first();
  await monday.click();
  await modal.getByRole("button", { name: ru["branches.removeInterval"], exact: true }).click();
  await modal.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(modal).not.toBeVisible();
  await expect.poll(async () => (await session.read(`branches/${f.second}/configuration`) as BranchConfiguration).days.some(day => day.resource === f.staff && day.date === "2030-01-07" && !day.intervals.length)).toBe(true);
  await page.getByRole("table").getByRole("button", { name: new RegExp(`Anna, .*${ru["workingHours.dayOff"]}`) }).first().click();
  await modal.getByRole("button", { name: ru["branches.removeOverride"], exact: true }).click();
  await expect(modal).not.toBeVisible();
  await page.getByRole("button", { name: ru["business.weekTemplate"], exact: true }).click();
  await modal.getByLabel(ru["branches.start"], { exact: true }).fill("09:00");
  await modal.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(modal.getByRole("status")).toBeVisible();
  await expect(modal.getByLabel(ru["branches.start"], { exact: true })).toHaveValue("09:00");
  await modal.getByLabel(ru["branches.start"], { exact: true }).fill("14:00");
  await modal.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(modal).not.toBeVisible();
  await page.getByRole("button", { name: ru["business.today"], exact: true }).click();
  const expected = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Almaty", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  await expect(page.getByLabel(ru["appointment.date"], { exact: true })).toHaveValue(expected);
  await page.screenshot({ path: info.outputPath("network-week.png"), fullPage: true });
  await noOverflow(page);
});

test("archive preserves working context, creates a visible empty branch and restores paused", async ({ page }) => {
  const f = fixtures.recovery;
  const session = await crmSession(page, f.email);
  const archived = await session.create<Branch>("branches", { name: "Archive test", address: "" });
  await session.action(`branches/${archived.id}/state`, { state: "archived" });
  await page.goto(`/app/business/branches?branch=${f.second}`);
  await page.getByRole("button", { name: ru["business.archive"], exact: true }).click();
  await expect(page.getByRole("heading", { name: "Archive test", exact: true })).toBeVisible();
  await nav(page).getByRole("link", { name: ru["business.staff"], exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`staff\\?branch=${f.second}$`));
  await page.goto(`/app/business/branches?branch=${f.second}&archived=1`);
  await page.getByRole("button", { name: ru["branches.add"], exact: true }).click();
  await page.getByLabel(ru["branches.name"], { exact: true }).fill("   ");
  await expect(page.getByRole("button", { name: ru["common.save"], exact: true })).toBeDisabled();
  await page.getByLabel(ru["branches.name"], { exact: true }).fill("New empty location");
  await page.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(page.getByRole("heading", { name: "New empty location", exact: true })).toBeVisible();
  await expect(page).not.toHaveURL(/archived=1/);
  const created = (await session.list<Branch>("branches")).find(branch => branch.name === "New empty location")!;
  const config = await session.read(`branches/${created.id}/configuration`) as BranchConfiguration;
  expect(config.assignments).toHaveLength(0);
  expect(config.offers).toHaveLength(0);
  await page.goto(`/app/business/branches?branch=${f.second}&archived=1&archived_branch=${archived.id}`);
  await page.getByRole("button", { name: ru["business.restorePaused"], exact: true }).click();
  await expect.poll(async () => (await session.read(`branches/${archived.id}`)).archived_at).toBe(null);
  expect((await session.read(`branches/${archived.id}`)).is_active).toBe(false);
});

for (const [language, dictionary, width] of [["kk", kk, 320], ["en", en, 390]] as const) {
  test(`mobile ${language} six sections, day selection, keyboard and error retry`, async ({ page }, info) => {
    const f = fixtures[language];
    await page.setViewportSize({ width, height: 844 });
    await crmSession(page, f.email);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    for (const section of ["company", "branches", "staff", "services", "resources", "working-hours"]) {
      await page.goto(`/app/business/${section}?branch=${f.second}`);
      await expect(nav(page, dictionary)).toBeVisible();
      await expect(nav(page, dictionary).getByRole("link")).toHaveCount(6);
      await expect(nav(page, dictionary).locator('a[aria-current="page"]')).toHaveCount(1);
      await expect(page.getByRole("heading", { level: 2 }).first()).toBeVisible();
      await noOverflow(page);
      await page.screenshot({ path: info.outputPath(`${language}-${section}-${width}.png`), fullPage: true });
    }
    const day = page.getByRole("button", { name: new RegExp(`^${dictionary["weekday.sunShort"]}`) });
    await day.focus();
    await page.keyboard.press("Enter");
    await expect(day).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: dictionary["business.today"], exact: true }).click();
    await page.route(`**/api/resources/**`, route => route.fulfill({ status: 503, json: { detail: "Temporary test outage" } }));
    await page.goto(`/app/business/resources?branch=${f.second}`);
    await expect(page.getByRole("alert")).toBeVisible();
    await page.unroute(`**/api/resources/**`);
    await page.getByRole("button", { name: dictionary["common.retry"], exact: true }).click();
    await expect(page.getByTestId("resource-row").filter({ visible: true })).toHaveCount(1);
    await noOverflow(page);
  });
}

test("manager can inspect company and catalogs without write actions", async ({ page }) => {
  const f = fixtures.network;
  await crmSession(page, f.manager_email);
  await page.goto("/app/business/company");
  await expect(page.getByLabel(ru["businessForm.name"], { exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: ru["businessForm.save"], exact: true })).toHaveCount(0);
  await nav(page).getByRole("link", { name: ru["business.staff"], exact: true }).click();
  await expect(page.getByRole("button", { name: ru["resources.add"], exact: true })).toBeDisabled();
  await page.getByTestId("resource-row").filter({ visible: true }).filter({ hasText: "Anna" }).click();
  await expect(page.getByRole("dialog", { name: "Anna", exact: true }).getByLabel(ru["resources.name"], { exact: true })).toBeDisabled();
});

test("automatic location weekly hours and absence appear in the real schedule", async ({ page }, info) => {
  const f = fixtures.single;
  const session = await crmSession(page, f.email);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/app/business/working-hours?branch=${f.branch}&date=2030-01-07`);
  await page.getByRole("button", { name: ru["business.weekTemplate"], exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(ru["branches.start"], { exact: true }).fill("10:00");
  await dialog.getByLabel(ru["branches.end"], { exact: true }).fill("16:00");
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("button", { name: /Anna, .*10:00–16:00/ })).toBeVisible();
  const rows = await session.list<{ resource: number; weekday: number; start_time: string }>("working-hours");
  expect(rows.find(row => row.resource === f.staff && row.weekday === 0)?.start_time).toBe("10:00:00");
  await page.goto(`/app/business/staff?branch=${f.branch}&resource=${f.staff}`);
  const staff = page.getByRole("dialog", { name: "Anna", exact: true });
  await staff.getByLabel(ru["branches.absenceStart"], { exact: true }).fill("2030-01-07");
  await staff.getByLabel(ru["branches.absenceEnd"], { exact: true }).fill("2030-01-08");
  await staff.getByRole("button", { name: ru["branches.addAbsence"], exact: true }).click();
  await expect(staff.getByRole("button", { name: ru["branches.removeAbsence"], exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await nav(page).getByRole("link", { name: ru["nav.workingHours"], exact: true }).click();
  await page.getByLabel(ru["appointment.date"], { exact: true }).fill("2030-01-07");
  await expect(page.getByRole("button", { name: new RegExp(`Anna, .*${ru["branches.absences"]}`) })).toBeVisible();
  await page.screenshot({ path: info.outputPath("single-absence-390.png"), fullPage: true });
  await noOverflow(page);
});
