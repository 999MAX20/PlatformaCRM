import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import { requireIsolatedEnvironment } from "./isolated-environment.mjs";

requireIsolatedEnvironment();
test.use({ actionTimeout: 15_000 });
async function login(page: Page, language: string, doctor = false) {
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(doctor ? "medical-role-doctor@example.test" : "medical-template-head@example.test");
  await page.locator('input[name="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/settings#medical-credentials");
  await expect(page.getByTestId("medical-credential-workspace")).toBeVisible();
}

for (const [language, t] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  for (const width of [1440, 390]) test(`credentials ${language} ${width}: confirmation history doctor read and recovery`, async ({ page, browser }, info) => {
    await page.setViewportSize({ width, height: 950 });
    await login(page, language);
    const workspace = page.getByTestId("medical-credential-workspace");
    const edit = workspace.getByRole("button", { name: t["medical.credentials.edit"], exact: true });
    await edit.click();
    const dialog = page.getByRole("dialog");
    const license = `Synthetic license ${language} ${width}`;
    await dialog.getByRole("textbox", { name: t["medical.credentials.license"], exact: true }).fill(license);
    let outage = true;
    const keys: (string | undefined)[] = [];
    await page.route("**/api/medical/credentials/", route => {
      if (route.request().method() !== "POST") return route.continue();
      keys.push(route.request().headers()["idempotency-key"]);
      return outage ? route.fulfill({ status: 503, json: { detail: "Synthetic credential outage" } }) : route.continue();
    });
    const save = dialog.getByRole("button", { name: t["medical.credentials.confirm"], exact: true });
    await save.click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await expect(dialog.getByRole("textbox", { name: t["medical.credentials.license"], exact: true })).toHaveValue(license);
    await dialog.screenshot({ path: info.outputPath("confirmation-retry.png") });
    outage = false; await save.click();
    await expect(dialog).not.toBeVisible();
    expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
    await expect(workspace.getByText(license, { exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath("clinic-confirmed.png") });
    await page.unroute("**/api/medical/credentials/");
    await workspace.getByRole("combobox").click();
    await workspace.getByRole("option", { name: "Synthetic clinician", exact: true }).click();
    await edit.click();
    const specialty = `Synthetic specialty ${language} ${width}`;
    await dialog.getByRole("textbox", { name: t["medical.credentials.specialty"], exact: true }).fill(specialty);
    await dialog.getByRole("textbox", { name: t["medical.credentials.position"], exact: true }).fill(`Synthetic position ${language}`);
    await dialog.getByRole("textbox", { name: t["medical.credentials.qualification"], exact: true }).fill("Synthetic qualification " + "Ә".repeat(300));
    await dialog.screenshot({ path: info.outputPath("doctor-editor.png") });
    expect((await new AxeBuilder({ page }).include('[role="dialog"]').analyze()).violations).toEqual([]);
    await save.click(); await expect(dialog).not.toBeVisible();
    await expect(workspace.getByText(specialty, { exact: true })).toBeVisible();
    await edit.click();
    await dialog.getByRole("textbox", { name: t["medical.credentials.specialty"], exact: true }).fill(`${specialty} revised`);
    await save.click(); await expect(dialog).not.toBeVisible();
    await expect(workspace.getByText(`${specialty} revised`, { exact: true })).toBeVisible();
    const history = workspace.getByRole("region", { name: t["medical.templates.history"], exact: true });
    await expect(history.getByRole("button").nth(1)).toBeVisible();
    await history.getByRole("button").nth(1).click();
    await expect(workspace.getByText(specialty, { exact: true })).toBeVisible();
    await expect(edit).toHaveCount(0);
    await page.screenshot({ path: info.outputPath("doctor-history.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const context = await browser.newContext({ viewport: { width, height: 950 } });
    const doctor = await context.newPage();
    try {
      await login(doctor, language, true);
      const own = doctor.getByTestId("medical-credential-workspace");
      await expect(own.getByText(`${specialty} revised`, { exact: true })).toBeVisible();
      await expect(own.getByRole("combobox")).toHaveCount(0);
      await expect(own.getByRole("button", { name: t["medical.credentials.edit"], exact: true })).toHaveCount(0);
      await doctor.screenshot({ path: info.outputPath("doctor-own-read.png") });
    } finally { await context.close(); }
  });
}

test("credentials: stale confirmation retains input and denial clears it", async ({ page }, info) => {
  await login(page, "ru");
  const workspace = page.getByTestId("medical-credential-workspace");
  await workspace.getByRole("button", { name: ru["medical.credentials.edit"], exact: true }).click();
  const dialog = page.getByRole("dialog");
  const field = dialog.getByRole("textbox", { name: ru["medical.credentials.license"], exact: true });
  await field.fill("Synthetic stale licence");
  await page.route("**/api/medical/credentials/", route => route.request().method() === "POST"
    ? route.fulfill({ status: 409, json: { detail: "Synthetic concurrent confirmation" } }) : route.continue());
  await dialog.getByRole("button", { name: ru["medical.credentials.confirm"], exact: true }).click();
  await expect(field).toHaveValue("Synthetic stale licence");
  await expect(field).toBeDisabled();
  await dialog.screenshot({ path: info.outputPath("conflict-retained.png") });
  page.once("dialog", prompt => void prompt.accept());
  await dialog.getByRole("button", { name: ru["medical.clinical.reload"], exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.unroute("**/api/medical/credentials/");
  await workspace.getByRole("button", { name: ru["medical.credentials.edit"], exact: true }).click();
  await field.fill("Synthetic denied licence");
  await page.route("**/api/medical/credentials/", route => route.request().method() === "POST"
    ? route.fulfill({ status: 403, json: { detail: "Synthetic revoked confirmation" } }) : route.continue());
  await dialog.getByRole("button", { name: ru["medical.credentials.confirm"], exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(workspace.getByRole("alert")).toBeVisible();
  await expect(workspace.getByRole("combobox")).toHaveCount(0);
  await expect(workspace.getByText("Synthetic denied licence", { exact: true })).toHaveCount(0);
  await workspace.screenshot({ path: info.outputPath("denied-cleared.png") });
});

test("credentials: empty read recovery, keyboard guards, pending save and history pages", async ({ page }, info) => {
  test.setTimeout(90_000);
  let unavailable = true;
  await page.route("**/api/medical/credentials/?*", route => unavailable
    ? route.fulfill({ status: 503, json: { detail: "Synthetic profile read outage" } }) : route.continue());
  await login(page, "en");
  const workspace = page.getByTestId("medical-credential-workspace");
  await expect(workspace.getByRole("alert")).toBeVisible();
  await workspace.screenshot({ path: info.outputPath("read-recovery.png") });
  unavailable = false;
  await workspace.getByRole("button", { name: en["common.retry"], exact: true }).click();
  const edit = workspace.getByRole("button", { name: en["medical.credentials.edit"], exact: true });
  await edit.click();
  const dialog = page.getByRole("dialog");
  await dialog.press("Escape");
  await expect(dialog).not.toBeVisible(); await expect(edit).toBeFocused();
  await edit.press("Enter");
  const field = dialog.getByRole("textbox", { name: en["medical.credentials.license"], exact: true });
  await field.fill("Synthetic keyboard licence");
  page.once("dialog", prompt => void prompt.dismiss()); await dialog.press("Escape");
  await expect(field).toHaveValue("Synthetic keyboard licence");
  let release: (() => void) | undefined;
  const held = new Promise<void>(resolve => { release = resolve; });
  let received = false;
  await page.route("**/api/medical/credentials/", async route => {
    if (route.request().method() === "POST") { received = true; await held; }
    await route.continue();
  });
  await dialog.getByRole("button", { name: en["medical.credentials.confirm"], exact: true }).click();
  await expect.poll(() => received).toBe(true);
  await expect(field).toBeDisabled(); await dialog.press("Escape"); await expect(dialog).toBeVisible();
  await dialog.screenshot({ path: info.outputPath("pending-save.png") });
  release!(); await expect(dialog).not.toBeVisible();
  await page.unroute("**/api/medical/credentials/");
  await expect(workspace.getByText("Synthetic keyboard licence", { exact: true })).toBeVisible();
  await edit.click(); await field.fill("Synthetic second keyboard licence");
  await dialog.getByRole("button", { name: en["medical.credentials.confirm"], exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.route("**/api/medical/credentials/revisions/**", async route => {
    const url = new URL(route.request().url()); url.searchParams.set("limit", "1");
    await route.fulfill({ response: await route.fetch({ url: url.toString() }) });
  });
  await workspace.getByRole("button", { name: en["medical.clinical.reload"], exact: true }).click();
  const history = workspace.getByRole("region", { name: en["medical.templates.history"], exact: true });
  await history.getByRole("button", { name: en["medical.templates.more"], exact: true }).click();
  await history.getByRole("button").nth(1).click();
  await expect(workspace.getByText("Synthetic keyboard licence", { exact: true })).toBeVisible();
  await workspace.screenshot({ path: info.outputPath("history-pagination.png") });
});
