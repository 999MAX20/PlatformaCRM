import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";

function totp(secret: string, offset = 0) {
  const bits = [...secret].map(c => "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".indexOf(c).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from(bits.match(/.{8}/g)!.map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offset));
  const digest = createHmac("sha1", key).update(counter).digest();
  return ((digest.readUInt32BE(digest[19] & 15) & 0x7fffffff) % 1000000).toString().padStart(6, "0");
}

test("required enrollment hides secrets and retries session loading without reusing the challenge", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1" || process.env.AUTH_PRIVILEGED_MFA_REQUIRED !== "true", "Requires isolated mandatory-MFA fixtures");
  test.setTimeout(90000);
  const email = process.env.E2E_OWNER_EMAIL || "business_owner@example.com";
  const password = process.env.E2E_PASSWORD || "ZaniTest123!";
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.locator('form input[type="password"]').fill(password);
  const started = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/start/"));
  await page.locator('form button[type="submit"]').click();
  const enrollment = await (await started).json();
  await expect(page.getByTestId("authenticator-qr")).toBeVisible();
  let invalid = "000000";
  while ([-1, 0, 1].some(offset => totp(enrollment.manual_key, offset) === invalid)) invalid = String(Number(invalid) + 1).padStart(6, "0");
  await page.getByLabel("Код подтверждения", { exact: true }).fill(invalid);
  await page.getByRole("button", { name: "Подключить защиту", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("authenticator-qr")).toBeVisible();
  let confirms = 0;
  page.on("request", r => { if (r.url().endsWith("/mfa/enrollment/confirm/")) confirms += 1; });
  const confirmedResponse = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/confirm/"));
  await page.getByLabel("Код подтверждения", { exact: true }).fill(totp(enrollment.manual_key));
  await page.getByLabel("Код подтверждения", { exact: true }).press("Enter");
  const response = await confirmedResponse;
  expect(response.ok()).toBeTruthy();
  const confirmed = await response.json();
  try {
    await expect(page.getByRole("heading", { name: "Вход подтверждён", exact: true })).toBeVisible();
    await expect(page.getByTestId("authenticator-qr")).toHaveCount(0);
    await expect(page.getByLabel("Код подтверждения", { exact: true })).toHaveCount(0);
    for (const code of confirmed.recovery_codes) await expect(page.getByText(code, { exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => sessionStorage.getItem("zani_mfa_pending"))).toBeNull();
    const signIn = page.getByRole("button", { name: "Войти", exact: true });
    await expect(signIn).toBeFocused();
    await page.route("**/api/auth/me/", route => route.fulfill({ status: 503, json: { detail: "Temporary session load failure" } }));
    await signIn.press("Enter");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(signIn).toBeEnabled();
    await page.unroute("**/api/auth/me/");
    await signIn.click();
    await expect(page).toHaveURL(/\/app\//);
    expect(confirms).toBe(1);
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

for (const locale of ["ru", "kk", "en"]) {
  test(`MFA login shell and confirmation ${locale}`, async ({ page }, testInfo) => {
    await page.addInitScript(({ locale, token }) => {
      localStorage.setItem("ai_smb_language", locale);
      sessionStorage.setItem("zani_mfa_pending", JSON.stringify({ code: "mfa_enrollment_required", challenge_token: token, method: "totp", expires_at: "2099-01-01T00:00:00Z" }));
    }, { locale, token: fixture.challenge_token });
    await page.route("**/api/auth/mfa/enrollment/start/", route => route.fulfill({ json: fixture }));
    await page.route("**/api/auth/mfa/enrollment/confirm/", route => route.fulfill({ json: { access: "public-ui-fixture", recovery_codes: ["MUST-NOT-BE-RENDERED"] } }));
    await page.goto("/mfa");
    await expect(page.getByTestId("authenticator-qr")).toBeVisible();
    await expect(page.getByRole("img", { name: "PlatformaCRM", exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.screenshot({ path: `../output/mfa-login-20261106/enroll-${locale}-${testInfo.project.name}.png` });
    const input = page.locator('input[autocomplete="one-time-code"]');
    await input.fill("123456");
    await input.press("Enter");
    await expect(page.getByTestId("authenticator-qr")).toHaveCount(0);
    await expect(page.getByText("MUST-NOT-BE-RENDERED")).toHaveCount(0);
    await expect(page.locator("form")).toHaveCount(0);
    const signIn = page.locator(".serenity-login__primary");
    await expect(signIn).toBeVisible();
    await expect(signIn).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.screenshot({ path: `../output/mfa-login-20261106/confirmed-${locale}-${testInfo.project.name}.png` });
  });
}

test("missing MFA challenge returns to login", async ({ page }) => {
  await page.goto("/mfa");
  await expect(page.getByRole("heading", { name: "Подтверждение устарело" })).toBeVisible();
  await page.getByRole("link", { name: "Вернуться ко входу", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});
