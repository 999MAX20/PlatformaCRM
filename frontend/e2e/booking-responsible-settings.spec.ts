import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures only"); });

test("AI booking responsible persists, cancels and clears through real settings API", async ({ page }, info) => {
  test.setTimeout(120_000);
  const session = await crmSession(page);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  const options = await session.read(`businesses/${session.business}/booking-responsible-options`);
  const candidate = options.find((item: { id: number }) => item.id !== session.userId) || options[0];
  await page.goto("/app/settings#business-profile");
  const select = page.getByRole("combobox", { name: "Ответственный за AI-записи" });
  const form = select.locator("xpath=ancestor::form");
  const save = form.locator('button[type="submit"]');
  await expect(select).toBeEnabled();
  await select.click();
  await page.getByRole("option", { name: candidate.label, exact: true }).click();
  const pending = page.waitForResponse(r => r.request().method() === "PATCH" && r.url().endsWith(`/businesses/${session.business}/`));
  await save.click();
  expect((await pending).ok()).toBeTruthy();
  await page.reload();
  await expect(select).toContainText(candidate.label);
  expect((await session.read(`businesses/${session.business}`)).ai_booking_responsible_user).toBe(candidate.id);
  await select.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Escape");
  await expect(select).toBeFocused();
  await select.click();
  await page.getByRole("option", { name: "Не выбран: передавать запись сотруднику", exact: true }).click();
  await form.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(select).toContainText(candidate.label);
  await expect(save).toBeDisabled();
  await page.screenshot({ path: info.outputPath("booking-settings.png"), fullPage: true });
  await select.click();
  await page.getByRole("option", { name: "Не выбран: передавать запись сотруднику", exact: true }).click();
  await save.click();
  await expect(save).toBeDisabled();
  await page.reload();
  await expect(select).toContainText("Не выбран");
  expect((await session.read(`businesses/${session.business}`)).ai_booking_responsible_user).toBeNull();
  for (const [locale, label] of [["kk", "AI"], ["en", "AI"]]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.reload();
    await expect(page.getByRole("combobox", { name: new RegExp(label) })).toBeEnabled();
    await page.screenshot({ path: info.outputPath(`booking-settings-${locale}.png`), fullPage: true });
  }
});

test("AI booking options recover from loading and server failure", async ({ page }) => {
  test.setTimeout(120_000);
  await crmSession(page);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  let fail = true;
  await page.route("**/booking-responsible-options/", async route => {
    if (fail) await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporarily unavailable" }) });
    else await route.continue();
  });
  await page.goto("/app/settings#business-profile");
  const select = page.getByRole("combobox", { name: "Ответственный за AI-записи" });
  await expect(select).toBeDisabled();
  const retry = page.getByRole("button", { name: /Повтор/ });
  await expect(retry).toBeVisible({ timeout: 30_000 });
  fail = false;
  await retry.click();
  await expect(select).toBeEnabled();
});

test("AI booking rejects a stale candidate and focuses the recoverable field", async ({ page }) => {
  test.setTimeout(120_000);
  const session = await crmSession(page);
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.route("**/booking-responsible-options/", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: [...await response.json(), { id: 999999, label: "Expired candidate" }] });
  });
  await page.goto("/app/settings#business-profile");
  const select = page.getByRole("combobox", { name: "Ответственный за AI-записи" });
  const form = select.locator("xpath=ancestor::form");
  await expect(select).toBeEnabled();
  await select.click();
  await page.getByRole("option", { name: "Expired candidate", exact: true }).click();
  const pending = page.waitForResponse(r => r.request().method() === "PATCH" && r.url().endsWith(`/businesses/${session.business}/`));
  await form.locator('button[type="submit"]').click();
  expect((await pending).status()).toBe(400);
  await expect(form.getByText("Select an available member of this business.", { exact: true })).toBeVisible();
  await expect(select).toBeFocused();
  expect((await session.read(`businesses/${session.business}`)).ai_booking_responsible_user).toBeNull();
  await select.click();
  await page.getByRole("option", { name: "Не выбран: передавать запись сотруднику", exact: true }).click();
  await expect(form.getByText("Select an available member of this business.", { exact: true })).not.toBeVisible();
});
