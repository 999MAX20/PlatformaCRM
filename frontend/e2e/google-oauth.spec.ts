import { createSign, createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const fixturePath = process.env.E2E_GOOGLE_FIXTURES;
test.skip(!fixturePath, "Requires disposable Google OAuth runtime");
const fixture = fixturePath ? JSON.parse(readFileSync(fixturePath, "utf8")) : {};
const dictionaries = { ru, kk, en };

async function google(page: Page, email: string, sub = email) {
  await page.exposeFunction("syntheticGoogleToken", (nonce: string) => {
    const now = Math.floor(Date.now() / 1000);
    const payload = [ { alg: "RS256", typ: "JWT", kid: "fixture" }, {
      iss: "https://accounts.google.com", aud: "synthetic-client", sub, email,
      email_verified: true, name: "Synthetic Google", nonce, iat: now, exp: now + 300,
    }].map(value => Buffer.from(JSON.stringify(value)).toString("base64url")).join(".");
    return `${payload}.${createSign("RSA-SHA256").update(payload).sign(fixture.private_key, "base64url")}`;
  });
  await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({
    contentType: "application/javascript", body: `let options;
      window.google = {accounts:{id:{initialize(value){options=value},renderButton(parent){
        const button=document.createElement('button'); button.textContent='Synthetic Google';
        button.onclick=async()=>options.callback({credential:await window.syntheticGoogleToken(options.nonce)});
        parent.appendChild(button);
      }}}};`,
  }));
}

for (const language of ["ru", "kk", "en"] as const) {
  test(`${language}: new Google owner accepts documents and creates one business`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    const email = `${language}-${info.project.name}@google-new.example.test`;
    await google(page, email);
    await page.goto("/login");
    await page.getByRole("button", { name: "Synthetic Google", exact: true }).click();
    await expect(page).toHaveURL(/\/google\/complete$/);
    await expect(page.getByRole("heading", { name: dictionaries[language]["googleAuth.signupTitle"] })).toBeVisible();
    await expect(page.locator('input[name="full_name"]')).toHaveValue("Synthetic Google");
    await page.locator('input[name="phone"]').fill("+77770001234");
    await page.locator('input[name="business_name"]').fill(`Synthetic ${language} ${info.project.name}`);
    await page.locator('input[name="city"]').fill("Almaty");
    await page.locator('form button[type="submit"]').click();
    await expect(page.locator("#google-documents-error")).toBeVisible();
    await expect(page.locator('input[name="phone"]')).toHaveValue("+77770001234");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${language}-google-signup.png`), fullPage: true });
    for (const checkbox of await page.getByRole("checkbox").all()) await checkbox.check();
    const response = page.waitForResponse(r => r.url().endsWith("/api/auth/google/signup/") && r.request().method() === "POST");
    await page.locator('form button[type="submit"]').click();
    expect((await response).status()).toBe(201);
    await expect(page).toHaveURL(/\/app(?:\/|$)/);
  });

  test(`${language}: existing email requires password login and explicit link`, async ({ page }, info) => {
    const email = `${language}-${info.project.name}@google-existing.example.test`;
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await google(page, email);
    await page.goto("/login");
    await page.getByRole("button", { name: "Synthetic Google", exact: true }).click();
    await expect(page.getByText(dictionaries[language]["googleAuth.loginFirst"])).toBeVisible();
    await page.getByRole("link", { name: dictionaries[language]["auth.submit"], exact: true }).click();
    await expect(page.getByRole("button", { name: "Synthetic Google" })).toHaveCount(0);
    await expect(page.locator('input[name="email"]')).toHaveValue(email);
    await page.locator('input[name="password"]').fill("ExistingSynthetic123");
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/google\/complete$/);
    const password = page.getByLabel(dictionaries[language]["auth.password"], { exact: true });
    await password.fill("IncorrectSynthetic123");
    await page.getByRole("button", { name: dictionaries[language]["googleAuth.linkSubmit"] }).click();
    await expect(page.getByText(dictionaries[language]["googleAuth.proofRequired"])).toBeVisible();
    await password.fill("ExistingSynthetic123");
    const eye = page.getByRole("button", { name: dictionaries[language]["auth.showPassword"], exact: true });
    await eye.focus(); await page.keyboard.press("Enter");
    await expect(password).toHaveAttribute("type", "text");
    await page.keyboard.press("Enter");
    await expect(password).toHaveAttribute("type", "password");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${language}-google-link.png`), fullPage: true });
    await page.getByRole("button", { name: dictionaries[language]["googleAuth.linkSubmit"] }).click();
    await expect(page.getByRole("heading", { name: dictionaries[language]["googleAuth.linked"] })).toBeVisible();
  });
}

test("expired flow offers restart without creating an account", async ({ page }, info) => {
  await page.goto("/google/complete");
  await expect(page.getByText(ru["googleAuth.expired"])).toBeVisible();
  await page.screenshot({ path: info.outputPath("google-expired.png"), fullPage: true });
  await page.getByRole("link", { name: ru["passwordReset.backToLogin"] }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("Google script failure can be retried without losing password form input", async ({ page }) => {
  await page.route("https://accounts.google.com/gsi/client", route => route.abort());
  await page.goto("/login");
  await page.locator('input[name="email"]').fill("retained@example.test");
  await expect(page.getByRole("button", { name: ru["common.retry"] })).toBeVisible();
  await page.unroute("https://accounts.google.com/gsi/client");
  await google(page, "retry@example.test");
  await page.getByRole("button", { name: ru["common.retry"] }).click();
  await expect(page.getByRole("button", { name: "Synthetic Google", exact: true })).toBeVisible();
  await expect(page.locator('input[name="email"]')).toHaveValue("retained@example.test");
});

for (const mode of ["known", "mfa"] as const) {
  test(`${mode}: existing Google identity enters the same account`, async ({ page }, info) => {
    const email = `${mode}-${info.project.name}@google.example.test`;
    await google(page, email);
    await page.goto("/login");
    const verification = page.waitForResponse(r => r.url().endsWith("/api/auth/google/verify/"));
    const currentUser = page.waitForResponse(r => r.url().endsWith("/api/auth/me/") && r.status() === 200);
    await page.getByRole("button", { name: "Synthetic Google", exact: true }).click();
    const response = await verification;
    if (mode === "mfa") {
      expect(response.status()).toBe(202);
      expect((await response.json()).access).toBeUndefined();
      await expect(page).toHaveURL(/\/mfa$/);
      const counter = Buffer.alloc(8);
      counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
      const digest = createHmac("sha1", Buffer.from(fixture.mfa_hex, "hex")).update(counter).digest();
      const offset = digest[digest.length - 1] & 15;
      const code = String((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, "0");
      await page.getByTestId("mfa-code-input").locator("input").fill(code);
      const verified = page.waitForResponse(r => r.url().endsWith("/api/auth/mfa/verify/"));
      await page.locator('form button[type="submit"]').click();
      expect((await verified).status()).toBe(200);
    } else expect(response.status()).toBe(200);
    await expect(page).toHaveURL(/\/app(?:\/|$)/);
    expect((await (await currentUser).json()).email).toBe(email);
  });
}

test("link continuation survives MFA and requires a fresh factor", async ({ page }, info) => {
  const email = `mfa-link-${info.project.name}@google.example.test`;
  await google(page, email);
  await page.goto("/login");
  await page.getByRole("button", { name: "Synthetic Google", exact: true }).click();
  await page.getByRole("link", { name: ru["auth.submit"], exact: true }).click();
  await page.locator('input[name="password"]').fill("ExistingSynthetic123");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/mfa$/);
  await page.getByRole("button", { name: ru["mfa.useRecoveryCode"] }).click();
  await page.getByLabel(ru["mfa.recoveryCodeLabel"], { exact: true }).fill(fixture.recovery[info.project.name][0]);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/google\/complete$/);
  await page.getByLabel(ru["auth.password"], { exact: true }).fill("ExistingSynthetic123");
  await page.getByLabel(ru["googleAuth.mfaCode"], { exact: true }).fill(fixture.recovery[info.project.name][0]);
  await page.getByRole("button", { name: ru["googleAuth.linkSubmit"] }).click();
  await expect(page.getByText(ru["googleAuth.proofRequired"])).toBeVisible();
  await page.getByLabel(ru["googleAuth.mfaCode"], { exact: true }).fill(fixture.recovery[info.project.name][1]);
  await page.screenshot({ path: info.outputPath("google-link-mfa.png"), fullPage: true });
  await page.getByRole("button", { name: ru["googleAuth.linkSubmit"] }).click();
  await expect(page.getByRole("heading", { name: ru["googleAuth.linked"] })).toBeVisible();
});
