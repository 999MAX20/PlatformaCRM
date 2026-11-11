import { readFileSync } from "node:fs";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { ManagementCatalog } from "../src/api/management";

type Fixture = { email: string; business: number; branch: number; staff: number; room: number; service: number; manager_email: string };
const fixtures: Record<string, Fixture> = process.env.MANAGEMENT_FIXTURE ? JSON.parse(readFileSync(process.env.MANAGEMENT_FIXTURE, "utf8")) : {};
test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1" || !process.env.MANAGEMENT_FIXTURE, "Requires disposable Management fixtures"); });

async function choose(page: Page, label: string, value: string, within: Page | Locator = page) {
  await within.getByRole("combobox", { name: new RegExp(`^${label} `) }).click();
  await page.getByRole("option", { name: value, exact: true }).click();
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}
async function save(dialog: Locator, dictionary = ru) {
  await dialog.getByRole("button", { name: dictionary["common.save"], exact: true }).click();
  await expect(dialog).not.toBeVisible();
}

test("five pages: real service, specialist and room links survive reload", async ({ page }, info) => {
  const f = fixtures.desktop;
  const session = await crmSession(page, f.email);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/app/business");
  await expect(page).toHaveURL(/business\/services/);
  await expect(page.getByTestId("management-workspace")).toBeVisible();
  const nav = page.getByRole("navigation", { name: ru["business.navigationLabel"], exact: true });
  await expect(nav.getByRole("link")).toHaveCount(5);
  await nav.getByRole("link", { name: ru["management.specialists"], exact: true }).click();
  await page.getByRole("button", { name: ru["management.addSpecialist"], exact: true }).first().click();
  let dialog = page.getByRole("dialog", { name: ru["management.addSpecialist"], exact: true });
  await dialog.getByLabel(ru["management.fullName"], { exact: true }).fill("Dana Management");
  await dialog.getByLabel(ru["management.profession"], { exact: true }).fill("Consultant");
  await dialog.getByRole("checkbox", { name: "Consultation", exact: true }).check();
  await save(dialog);
  let catalog = await session.read("management", { business: f.business }) as ManagementCatalog;
  const specialist = catalog.resources.find(row => row.name === "Dana Management")!;
  expect(specialist).toBeTruthy();
  expect(catalog.assignments.find(row => row.resource === specialist.id)?.service_ids).toEqual([f.service]);
  await nav.getByRole("link", { name: ru["nav.services"], exact: true }).click();
  await page.getByRole("button", { name: "Consultation", exact: true }).click();
  dialog = page.getByRole("dialog", { name: ru["management.editService"], exact: true });
  await expect(dialog.getByRole("checkbox", { name: "Dana Management", exact: true })).toBeChecked();
  await dialog.getByLabel(ru["management.price"], { exact: true }).fill("0");
  await dialog.getByRole("checkbox", { name: ru["management.requiresRoom"], exact: true }).check();
  await dialog.getByRole("checkbox", { name: "Main room", exact: true }).check();
  await save(dialog);
  await page.reload();
  await expect(page.locator("tbody")).toContainText(ru["management.free"]);
  await expect(page.locator("tbody")).toContainText("Dana Management");
  catalog = await session.read("management", { business: f.business }) as ManagementCatalog;
  expect(catalog.services.find(row => row.id === f.service)?.price_from).toBe("0.00");
  expect(catalog.room_options.some(row => row.resource_id === f.room && row.service_id === f.service)).toBe(true);
  await page.screenshot({ path: info.outputPath("services-desktop.png"), fullPage: true });
  await nav.getByRole("link", { name: ru["management.rooms"], exact: true }).click();
  await expect(page.locator("tbody")).toContainText("Consultation");
  await page.getByRole("button", { name: ru["management.addRoom"], exact: true }).first().click();
  dialog = page.getByRole("dialog", { name: ru["management.addRoom"], exact: true });
  await dialog.getByLabel(ru["management.name"], { exact: true }).fill("Second room");
  await dialog.getByRole("checkbox", { name: "Consultation", exact: true }).check();
  await save(dialog);
  await nav.getByRole("link", { name: ru["branches.title"], exact: true }).click();
  await expect(page.getByRole("article")).toContainText("Second room");
  await page.getByRole("button", { name: ru["common.edit"], exact: true }).click();
  dialog = page.getByRole("dialog", { name: ru["management.editBranch"], exact: true });
  await dialog.getByLabel(ru["management.city"], { exact: true }).fill("Almaty");
  await dialog.getByLabel(ru["management.address"], { exact: true }).fill("Example street 22");
  await save(dialog);
  await page.reload();
  await expect(page.getByRole("article")).toContainText("Almaty, Example street 22");
  await page.screenshot({ path: info.outputPath("branch-desktop.png"), fullPage: true });
  await nav.getByRole("link", { name: ru["nav.workingHours"], exact: true }).click();
  await expect(page.getByRole("table")).toContainText("Anna");
  await expect(page.getByRole("table")).toContainText(`Management desktop`);
  await expect(page.getByText("Asia/Almaty", { exact: true })).toBeVisible();
  await noOverflow(page);
  await page.screenshot({ path: info.outputPath("schedule-desktop.png"), fullPage: true });
});

test("save error retains fields, draft guard, date-effective schedule and absences", async ({ page }, info) => {
  const f = fixtures.recovery;
  const session = await crmSession(page, f.email);
  await page.goto("/app/business/services");
  await page.getByRole("button", { name: ru["management.addService"], exact: true }).first().click();
  let dialog = page.getByRole("dialog", { name: ru["management.addService"], exact: true });
  await dialog.getByLabel(ru["management.name"], { exact: true }).fill("Recovery service");
  await page.route("**/api/management/services/", route => route.fulfill({ status: 503, json: { detail: "Temporary test failure" } }), { times: 1 });
  await dialog.getByRole("button", { name: ru["common.save"], exact: true }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog.getByLabel(ru["management.name"], { exact: true })).toHaveValue("Recovery service");
  await save(dialog);
  await page.goto(`/app/business/working-hours?branch=${f.branch}&resource=${f.staff}&date=2030-01-07`);
  await page.getByRole("button", { name: ru["business.weekTemplate"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel(ru["management.effectiveFrom"], { exact: true }).fill("2030-01-14");
  await dialog.getByLabel(ru["branches.start"], { exact: true }).fill("10:00");
  await save(dialog);
  const config = await session.read(`branches/${f.branch}/configuration`);
  expect(config.days.some((row: { resource: number; effective_from: string; intervals: { start: string }[] }) => row.resource === f.staff && row.effective_from === "2030-01-14" && row.intervals[0].start === "10:00")).toBe(true);
  await page.goto(`/app/business/staff`);
  await page.getByLabel(`${ru["management.actions"]}: Anna`, { exact: true }).click();
  await page.getByRole("button", { name: ru["management.unavailability"], exact: true }).click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel(ru["branches.absenceStart"], { exact: true }).fill("2030-02-01");
  await dialog.getByLabel(ru["branches.absenceEnd"], { exact: true }).fill("2030-02-02");
  await save(dialog);
  expect(await session.read(`resources/${f.staff}/absences`)).toHaveLength(1);
  await page.getByRole("button", { name: "Anna", exact: true }).click();
  dialog = page.getByRole("dialog", { name: ru["management.editSpecialist"], exact: true });
  await dialog.getByLabel(ru["management.fullName"], { exact: true }).fill("Unsaved name");
  await dialog.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(2);
  await page.getByRole("button", { name: ru["actions.discardChanges"], exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Anna", exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath("recovery-staff.png"), fullPage: true });
});

for (const [label, dictionary, width] of [["mobile", ru, 320], ["kk", kk, 390], ["en", en, 768]] as const) {
  test(`${label} responsive navigation, all five pages and keyboard form`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    await crmSession(page, fixtures[label].email);
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), label === "mobile" ? "ru" : label);
    await page.goto("/app/business/services");
    for (const key of ["nav.services", "management.specialists", "management.rooms", "branches.title", "nav.workingHours"]) {
      await choose(page, dictionary["management.section"], dictionary[key]);
      await expect(page.getByRole("heading", { name: new RegExp(`^${dictionary[key]}`) }).first()).toBeVisible();
      await noOverflow(page);
      await page.screenshot({ path: info.outputPath(`${label}-${key.replace(".", "-")}.png`), fullPage: true });
    }
    await choose(page, dictionary["management.section"], dictionary["management.rooms"]);
    await page.getByRole("button", { name: dictionary["management.addRoom"], exact: true }).first().click();
    const dialog = page.getByRole("dialog", { name: dictionary["management.addRoom"], exact: true });
    await dialog.getByLabel(dictionary["management.name"], { exact: true }).fill(`Room ${label}`);
    await page.keyboard.press("Tab");
    await noOverflow(page);
    await page.screenshot({ path: info.outputPath(`${label}-room-form.png`), fullPage: true });
    await save(dialog, dictionary);
    await expect(page.locator("tbody")).toContainText(`Room ${label}`);
  });
}

test("manager views real data without configuration writes", async ({ page }) => {
  const f = fixtures.desktop;
  const session = await crmSession(page, f.manager_email);
  await page.goto("/app/business/services");
  await expect(page.locator("tbody")).toContainText("Consultation");
  await expect(page.getByRole("button", { name: ru["management.addService"], exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: ru["common.edit"], exact: true })).toHaveCount(0);
  const response = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/management/services/`, { headers: session.headers, data: { business: f.business, name: "Denied", duration_minutes: 30, price_from: null, locations: [] } });
  expect(response.status()).toBe(403);
});


test("service activity, archive, restore and unused deletion persist", async ({ page }) => {
  const f = fixtures.recovery;
  const session = await crmSession(page, f.email);
  await page.goto("/app/business/services");
  await page.getByRole("button", { name: ru["management.addService"], exact: true }).first().click();
  const dialog = page.getByRole("dialog", { name: ru["management.addService"], exact: true });
  await dialog.getByLabel(ru["management.name"], { exact: true }).fill("Lifecycle service");
  await dialog.getByRole("checkbox", { name: ru["management.active"], exact: true }).uncheck();
  await dialog.getByRole("checkbox", { name: "Management recovery", exact: true }).uncheck();
  await save(dialog);
  let catalog = await session.read("management", { business: f.business }) as ManagementCatalog;
  const id = catalog.services.find(row => row.name === "Lifecycle service")!.id;
  expect(catalog.services.find(row => row.id === id)?.is_active).toBe(false);
  const perform = async (operation: "activate" | "archive" | "restore" | "delete") => {
    await page.getByLabel(`${ru["management.actions"]}: Lifecycle service`, { exact: true }).click();
    await page.getByRole("button", { name: ru[`management.${operation}`], exact: true }).click();
    await page.getByRole("dialog").getByRole("button", { name: ru[`management.${operation}`], exact: true }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect.poll(async () => {
      catalog = await session.read("management", { business: f.business }) as ManagementCatalog;
      const row = catalog.services.find(item => item.id === id);
      return operation === "delete" ? !row : operation === "activate" ? row?.is_active : operation === "archive" ? row?.is_archived : row && !row.is_archived && !row.is_active;
    }).toBeTruthy();
    await page.reload();
  };
  await perform("activate");
  await perform("archive");
  await choose(page, ru["management.state"], ru["management.archived"]);
  await perform("restore");
  await choose(page, ru["management.state"], ru["management.current"]);
  await perform("delete");
});
