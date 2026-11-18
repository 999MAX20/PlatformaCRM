import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { en } from "../src/lib/i18n/en";
import { kk } from "../src/lib/i18n/kk";

test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required"); test.setTimeout(120_000); });

test("company draft survives internal navigation and asks before leaving", async ({ page }, info) => {
  await crmSession(page);
  await page.goto("/app/settings#business-profile");
  const panel = page.locator("#business-profile");
  await panel.getByLabel(ru["businessForm.city"], { exact: true }).fill("Unsaved city");
  const nav = page.locator(".settings-workspace > aside");
  if (await nav.getByRole("combobox").isVisible()) {
    await nav.getByRole("combobox").click();
    await nav.getByRole("option", { name: ru["settings.section.appointment-messages"], exact: true }).click();
  } else await nav.getByRole("link", { name: ru["settings.section.appointment-messages"], exact: true }).click();
  await expect(page.locator("#appointment-messages")).toBeVisible();
  await page.getByRole("link", { name: ru["nav.clients"], exact: true }).first().click();
  const confirm = page.getByRole("dialog");
  await expect(confirm).toBeVisible();
  await confirm.getByRole("button", { name: ru["taskWorkspace.keepEditing"], exact: true }).click();
  await expect(page).toHaveURL(/settings/);
  await page.getByRole("link", { name: ru["nav.clients"], exact: true }).first().click();
  await confirm.getByRole("button", { name: ru["taskWorkspace.discard"], exact: true }).click();
  await expect(page).toHaveURL(/\/clients/);
  await page.goto("/app/settings#business-profile");
  await panel.locator('[data-business-timezone] button').first().click();
  await panel.locator('[data-business-timezone] input').fill("Қызылорда");
  await expect(panel.getByRole("option", { name: /Кызылорда/ })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.screenshot({ path: info.outputPath("company.png"), fullPage: true });
  await page.goto("/app/business/company");
  await expect(page.locator('[data-business-timezone]')).toBeVisible();
});

test("scenario switch, text and duration save together and recover after rejection", async ({ page }, info) => {
  await crmSession(page);
  await page.goto("/app/settings#appointment-messages");
  const panel = page.locator("#appointment-messages");
  const sent: Record<string, unknown>[] = [];
  page.on("request", request => { if (request.method() === "PATCH" && request.url().includes("appointment-message-settings")) sent.push(request.postDataJSON()); });
  const original = await panel.getByRole("switch").isChecked();
  const message = `Hello ${info.project.name} {client_name}`;
  const hours = info.project.name === "mobile-chromium" ? 3 : 2;
  await panel.getByRole("switch").click();
  await panel.locator("textarea").fill(message);
  await panel.getByRole("combobox", { name: /Единица времени/ }).click();
  await page.getByRole("option", { name: "Часы", exact: true }).click();
  await panel.getByRole("spinbutton").fill(String(hours));
  expect(sent).toEqual([]);
  await page.route("**/api/appointment-message-settings/*/", route => route.request().method() === "PATCH" ? route.fulfill({ status: 503, json: { detail: "Unavailable" } }) : route.continue(), { times: 1 });
  const save = panel.getByRole("button", { name: ru["settings.appointmentMessages.saveScenario"], exact: true });
  await save.click();
  await expect(panel.getByRole("alert")).toBeVisible();
  await expect(panel.locator("textarea")).toHaveValue(message);
  await expect(panel.getByRole("switch")).toBeChecked({ checked: !original });
  await save.click();
  await expect(save).toBeDisabled();
  expect(sent.at(-1)).toMatchObject({ is_enabled: !original, offset_minutes: -hours * 60, template_text: message });
  await page.screenshot({ path: info.outputPath("messages.png"), fullPage: true });
  await panel.getByRole("switch").click();
  await panel.getByRole("button", { name: ru["common.cancel"], exact: true }).click();
  await expect(save).toBeDisabled();
});

test("security filtering is server side and history remains paginated", async ({ page }, info) => {
  await crmSession(page);
  await page.goto("/app/settings#security-center");
  const panel = page.locator("#security-center");
  await panel.getByRole("button", { name: ru["settings.redesign.loginsTab"], exact: true }).click();
  const filtered = page.waitForRequest(request => request.url().includes("/security/login-history/") && request.url().includes("status=failed") && request.url().includes("paginate=true"));
  await panel.getByRole("checkbox", { name: ru["settings.workflow.failedOnly"], exact: true }).check();
  await filtered;
  await panel.getByRole("combobox", { name: /Период/ }).click();
  const period = page.waitForRequest(request => request.url().includes("/security/login-history/") && request.url().includes("date_from=") && request.url().includes("page=1"));
  await page.getByRole("option", { name: "Последние 7 дней", exact: true }).click();
  await period;
  await expect(panel.getByRole("alert")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("security.png"), fullPage: true });
});

test("security filtering and compact navigation remain localized", async ({ page }, info) => {
  await crmSession(page);
  for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/app/settings#custom-fields");
    await page.reload();
    const panel = page.locator("#custom-fields");
    await panel.getByRole("button", { name: copy["records.historical"], exact: true }).click();
    await panel.getByRole("combobox").click();
    await page.getByRole("option", { name: copy["settings.customFieldEntity.deal"], exact: true }).click();
    await expect(panel.getByRole("button", { name: copy["settings.redesign.addField"], exact: true })).toBeDisabled();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`fields-${language}.png`), fullPage: true });
    await page.goto("/app/settings#voice-input");
    await expect(page.getByText(copy["settings.clarity.voiceLocal"], { exact: true })).toBeVisible();
    await page.goto("/app/settings#appointment-messages");
    await expect(page.getByRole("combobox", { name: new RegExp(copy["settings.clarity.unit"]) })).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`messages-${language}.png`), fullPage: true });
  }
});
