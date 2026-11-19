import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const dictionaries = { ru, kk, en };

for (const language of ["ru", "kk", "en"] as const) {
  test(`${language}: reset eyes are independent, keyboard-operable and retain input`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/login");
    const background = await page.locator("main").evaluate(element => getComputedStyle(element).backgroundImage);
    const loginEye = page.getByRole("button", { name: dictionaries[language]["auth.showPassword"], exact: true });
    const loginStyle = await loginEye.evaluate(element => [getComputedStyle(element).backgroundColor, getComputedStyle(element).color]);
    await loginEye.hover();
    expect(await loginEye.evaluate(element => [getComputedStyle(element).backgroundColor, getComputedStyle(element).color])).toEqual(loginStyle);
    await page.goto("/reset-password/synthetic/unused-link");
    expect(await page.locator("main").evaluate(element => getComputedStyle(element).backgroundImage)).toBe(background);
    const first = page.locator('input[name="password"]');
    const repeat = page.locator('input[name="password_confirm"]');
    await first.fill("SyntheticOnly928!");
    await repeat.fill("Different928!");
    const show = page.getByRole("button", { name: dictionaries[language]["auth.showPassword"], exact: true });
    await expect(show).toHaveCount(2);
    const target = await show.first().boundingBox();
    expect(target?.width).toBeGreaterThanOrEqual(44);
    expect(target?.height).toBeGreaterThanOrEqual(44);
    const eyeStyle = await show.first().evaluate(element => [getComputedStyle(element).backgroundColor, getComputedStyle(element).color]);
    await show.first().hover();
    expect(await show.first().evaluate(element => [getComputedStyle(element).backgroundColor, getComputedStyle(element).color])).toEqual(eyeStyle);
    await show.first().focus();
    await show.first().press("Space");
    await expect(first).toHaveAttribute("type", "text");
    await expect(repeat).toHaveAttribute("type", "password");
    await expect(first).toHaveValue("SyntheticOnly928!");
    const hide = page.getByRole("button", { name: dictionaries[language]["auth.hidePassword"], exact: true });
    await expect(hide).toBeFocused();
    await page.screenshot({ path: info.outputPath(`${language}-eye-focus.png`), fullPage: true });
    await hide.press("Enter");
    await expect(first).toHaveAttribute("type", "password");
    await page.getByRole("button", { name: dictionaries[language]["passwordReset.savePassword"], exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(dictionaries[language]["passwordReset.passwordMismatch"]);
    await expect(first).toHaveValue("SyntheticOnly928!");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${language}-reset.png`), fullPage: true });
  });

  test(`${language}: forgot background, localized confirmation and lost-access removal`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/login");
    const background = await page.locator("main").evaluate(element => getComputedStyle(element).backgroundImage);
    await expect(page.locator('a[href="/recover-account"]')).toHaveCount(0);
    await page.goto("/recover-account");
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/forgot-password");
    expect(await page.locator("main").evaluate(element => getComputedStyle(element).backgroundImage)).toBe(background);
    await expect(page.getByRole("button", { name: dictionaries[language]["auth.showPassword"], exact: true })).toHaveCount(0);
    await page.route("**/api/auth/password-reset/request/", route => route.fulfill({ json: { message: "If this account exists, a password reset link will be sent." } }));
    await page.getByLabel("Email", { exact: true }).fill("synthetic@example.com");
    await page.getByRole("button", { name: dictionaries[language]["passwordReset.getLink"], exact: true }).click();
    await expect(page.getByRole("status")).toContainText(dictionaries[language]["passwordReset.requestSent"]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${language}-forgot.png`), fullPage: true });
  });
}

test("support-issued recovery link still opens its password form", async ({ page }) => {
  await page.goto(`/recover-account#00000000-0000-4000-8000-000000000000/${"a".repeat(43)}`);
  await expect(page.getByRole("heading", { name: ru["recovery.title"] })).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(2);
  await expect(page.getByRole("button", { name: ru["auth.showPassword"], exact: true })).toHaveCount(2);
  await expect(page).toHaveURL(/\/recover-account$/);
});

test("forgot request retains email after failure and allows a safe retry", async ({ page }) => {
  await page.goto("/forgot-password");
  let requests = 0;
  await page.route("**/api/auth/password-reset/request/", async route => {
    requests += 1;
    if (requests === 1) await route.fulfill({ status: 503, json: { code: "service_unavailable" } });
    else {
      await new Promise(resolve => setTimeout(resolve, 300));
      await route.fulfill({ json: { message: "Accepted" } });
    }
  });
  const email = page.getByLabel("Email", { exact: true });
  const submit = page.locator('form button[type="submit"]');
  await email.fill("synthetic@example.com");
  await submit.click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(email).toHaveValue("synthetic@example.com");
  await submit.click();
  await expect(submit).toBeDisabled();
  await expect(page.getByRole("status")).toContainText(ru["passwordReset.requestSent"]);
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(requests).toBe(2);
});

test("invalid reset link explains recovery and offers a fresh request", async ({ page }) => {
  await page.goto("/reset-password/synthetic/invalid-link");
  await page.locator('input[name="password"]').fill("SyntheticOnly928!");
  await page.locator('input[name="password_confirm"]').fill("SyntheticOnly928!");
  await page.getByRole("button", { name: ru["passwordReset.savePassword"], exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(ru["passwordReset.invalidLink"]);
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await page.getByRole("link", { name: ru["passwordReset.getLink"], exact: true }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
});

test("server policy error stays at the password field; corrected password resets and can log in", async ({ page }, info) => {
  test.skip(!process.env.E2E_AUTH_FORMS_FIXTURES, "Requires isolated auth-form fixture tokens");
  const fixture = JSON.parse(readFileSync(process.env.E2E_AUTH_FORMS_FIXTURES!, "utf8"))[info.project.name];
  await page.goto(fixture.path);
  await page.locator('input[name="password"]').fill("12345678");
  await page.locator('input[name="password_confirm"]').fill("12345678");
  await page.getByRole("button", { name: ru["passwordReset.savePassword"], exact: true }).click();
  await expect(page.locator('input[name="password"]')).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator('input[name="password"]')).toBeFocused();
  await expect(page.getByRole("alert")).not.toContainText(ru["actions.errorValidation"]);
  await expect(page.locator('input[name="password"]')).toHaveValue("12345678");
  await page.locator('input[name="password"]').fill("CorrectedSynthetic928!");
  await page.locator('input[name="password_confirm"]').fill("CorrectedSynthetic928!");
  await page.getByRole("button", { name: ru["passwordReset.savePassword"], exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.locator('input[name="email"]').fill(fixture.email);
  await page.locator('input[name="password"]').fill("CorrectedSynthetic928!");
  const login = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  expect((await login).ok()).toBe(true);
});
