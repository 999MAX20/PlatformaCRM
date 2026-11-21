import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

function totp(secret: string, offset = 0) {
  const bits = [...secret].map(c => "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".indexOf(c).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from(bits.match(/.{8}/g)!.map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offset));
  const digest = createHmac("sha1", key).update(counter).digest();
  return ((digest.readUInt32BE(digest[19] & 15) & 0x7fffffff) % 1000000).toString().padStart(6, "0");
}

test("voluntary enrollment retries profile loading and next login never starts a QR", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated MFA fixtures");
  test.setTimeout(90000);
  const email = process.env.E2E_OWNER_EMAIL || "business_owner@example.com";
  const password = process.env.E2E_PASSWORD || "ZaniTest123!";
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.locator('form input[type="password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app\//);
  await page.goto("/app/account");
  const started = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/start/"));
  await page.getByRole("button", { name: "Подключить MFA", exact: true }).click();
  const enrollment = await (await started).json();
  // Resume the user's pending enrollment in the public flow to exercise session recovery.
  await page.evaluate(data => sessionStorage.setItem("zani_mfa_pending", JSON.stringify({
    code: "mfa_enrollment_required", ...data,
  })), enrollment);
  await page.context().clearCookies();
  await page.goto("/mfa");
  await expect(page.getByTestId("authenticator-qr")).toBeVisible();
  let invalid = "000000";
  while ([-1, 0, 1].some(offset => totp(enrollment.manual_key, offset) === invalid)) invalid = String(Number(invalid) + 1).padStart(6, "0");
  await page.getByLabel("Код подтверждения", { exact: true }).fill(invalid);
  await page.getByRole("button", { name: "Подключить защиту", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("authenticator-qr")).toBeVisible();
  let confirms = 0;
  page.on("request", r => { if (r.url().endsWith("/mfa/enrollment/confirm/")) confirms += 1; });
  await page.route("**/api/auth/me/", route => route.fulfill({ status: 503, json: { detail: "Temporary session load failure" } }));
  const confirmedResponse = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/confirm/"));
  await page.getByLabel("Код подтверждения", { exact: true }).fill(totp(enrollment.manual_key));
  await page.getByLabel("Код подтверждения", { exact: true }).press("Enter");
  const response = await confirmedResponse;
  expect(response.ok()).toBeTruthy();
  const confirmed = await response.json();
  try {
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByTestId("authenticator-qr")).toHaveCount(0);
    await expect(page.getByLabel("Код подтверждения", { exact: true })).toHaveCount(0);
    for (const code of confirmed.recovery_codes) await expect(page.getByText(code, { exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => sessionStorage.getItem("zani_mfa_pending"))).toBeNull();
    await expect(page.getByRole("button", { name: "Войти", exact: true })).toHaveCount(0);
    const retry = page.getByRole("button", { name: "Повторить", exact: true });
    await expect(retry).toBeFocused();
    await page.unroute("**/api/auth/me/");
    await retry.press("Enter");
    await expect(page).toHaveURL(/\/app\//);
    expect(confirms).toBe(1);
    await page.goto("/app/account");
    await page.getByTestId("merchant-logout").click();
    await expect(page).toHaveURL(/\/login/);
    let starts = 0;
    page.on("request", r => { if (r.url().endsWith("/mfa/enrollment/start/")) starts++; });
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.locator('form input[type="password"]').fill(password);
    const nextChallenge = page.waitForResponse(r => r.url().endsWith("/api/auth/token/"));
    await page.locator('form button[type="submit"]').click();
    expect((await (await nextChallenge).json()).code).toBe("mfa_required");
    await expect(page).toHaveURL(/\/mfa/);
    await expect(page.getByTestId("authenticator-qr")).toHaveCount(0);
    await page.getByLabel("Код подтверждения", { exact: true }).fill(totp(enrollment.manual_key, 1));
    const verification = page.waitForResponse(r => r.url().endsWith("/mfa/verify/"));
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    const verified = await verification;
    expect(verified.ok()).toBe(true);
    confirmed.access = (await verified.json()).access;
    await expect(page).toHaveURL(/\/app\//);
    expect(starts).toBe(0);
  } finally {
    const disabled = await page.request.post(`${process.env.E2E_API_BASE_URL}/api/auth/mfa/disable/`, {
      headers: { Authorization: `Bearer ${confirmed.access}` },
      data: { password, code: confirmed.recovery_codes[0], reason: "Isolated MFA login test cleanup" },
    });
    expect(disabled.ok()).toBeTruthy();
  }
});

const fixture = {
  challenge_token: "public-ui-fixture", manual_key: "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
  otpauth_uri: "otpauth://totp/PlatformaCRM:test%40example.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=PlatformaCRM",
  issuer: "PlatformaCRM", account: "test@example.com", expires_at: "2099-01-01T00:00:00Z",
};

for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`six MFA cells support keyboard, paste, recovery and retry ${locale}`, async ({ page }, testInfo) => {
    await page.addInitScript(({ locale, token }) => {
      localStorage.setItem("ai_smb_language", locale);
      sessionStorage.setItem("zani_mfa_pending", JSON.stringify({ code: "mfa_required", challenge_token: token, method: "totp", expires_at: "2099-01-01T00:00:00Z" }));
    }, { locale, token: fixture.challenge_token });
    let starts = 0;
    let submitted = "";
    await page.route("**/api/auth/mfa/enrollment/start/", route => { starts++; return route.fulfill({ json: fixture }); });
    await page.route("**/api/auth/mfa/verify/", route => {
      submitted = route.request().postDataJSON().code;
      return route.fulfill({ status: 401, json: { code: "mfa_code_invalid", detail: "Invalid code" } });
    });
    await page.goto("/mfa");
    await expect(page.getByTestId("authenticator-qr")).toHaveCount(0);
    await expect(page.getByRole("img", { name: "PlatformaCRM", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    const input = page.locator('input[autocomplete="one-time-code"]');
    await input.focus();
    await input.pressSequentially("123456");
    await input.press("ArrowLeft");
    await input.press("Backspace");
    await expect(input).toHaveValue("12346");
    await input.press("5");
    await expect(input).toHaveValue("123456");
    await input.evaluate(element => {
      const data = new DataTransfer(); data.setData("text/plain", "987 654");
      element.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }));
    });
    await expect(input).toHaveValue("987654");
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await input.focus();
      await page.screenshot({ path: testInfo.outputPath(`mfa-${locale}-${width}.png`), fullPage: true });
    }
    if (locale === "ru") {
      const accessibility = await new AxeBuilder({ page }).include(".serenity-login__card").withTags(["wcag2a", "wcag2aa"]).analyze();
      expect(accessibility.violations).toEqual([]);
      await page.setViewportSize({ width: 640, height: 900 });
      await page.evaluate(() => { document.body.style.zoom = "2"; });
      const back = page.getByRole("link", { name: copy["mfa.backToLogin"], exact: true });
      await back.focus();
      await back.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath("mfa-ru-200-percent.png"), fullPage: true });
      await page.evaluate(() => { document.body.style.zoom = ""; });
    }
    await input.press("Enter");
    await expect(page.getByRole("alert")).toBeVisible();
    expect(submitted).toBe("987654");
    await expect(input).toHaveValue("987654");
    await page.getByRole("button", { name: copy["mfa.useRecoveryCode"], exact: true }).click();
    await page.getByLabel(copy["mfa.recoveryCodeLabel"], { exact: true }).fill("RECOVERY-TEST");
    await page.getByRole("button", { name: copy["auth.submit"], exact: true }).click();
    await expect.poll(() => submitted).toBe("RECOVERY-TEST");
    await page.getByRole("button", { name: copy["mfa.useAuthenticator"], exact: true }).click();
    await expect(input).toHaveValue("");
    expect(starts).toBe(0);
    const back = page.getByRole("link", { name: copy["mfa.backToLogin"], exact: true });
    await back.focus();
    await expect(back).toBeFocused();
    await back.press("Enter");
    await expect(page).toHaveURL(/\/login$/);
  });
}

test("missing MFA challenge returns to login", async ({ page }) => {
  await page.goto("/mfa");
  await expect(page.getByRole("heading", { name: "Подтверждение устарело" })).toBeVisible();
  await page.getByRole("link", { name: "Вернуться ко входу", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});
