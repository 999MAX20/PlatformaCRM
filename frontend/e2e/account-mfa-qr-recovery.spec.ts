import { expect, test } from "@playwright/test";

test("expired enrollment can be closed and restarted with a fresh QR", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated fixtures");
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  const start = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/start/"));
  await page.getByRole("button", { name: "Подключить MFA" }).click();
  const first = await (await start).json();
  // Server expiry is covered in tests_mfa; exercise its UI response without sleeping.
  await page.route("**/api/auth/mfa/enrollment/confirm/", route => route.fulfill({ status: 401, json: { code: "mfa_challenge_invalid", detail: "MFA challenge is unavailable or expired." } }));
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Код подтверждения").fill("000000");
  await dialog.getByRole("button", { name: "Подключить защиту" }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await dialog.getByRole("button", { name: "Закрыть", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  const restart = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/start/"));
  await page.getByRole("button", { name: "Подключить MFA" }).click();
  const second = await (await restart).json();
  expect(second.otpauth_uri).not.toBe(first.otpauth_uri);
  await expect(dialog.getByTestId("authenticator-qr")).toBeVisible();
  await expect(dialog.getByRole("alert")).toHaveCount(0);
  await expect(dialog.getByLabel("Код подтверждения")).toHaveValue("");
});

test("required enrollment at login displays the shared QR and manual fallback", async ({ page }) => {
  // Public RFC test secret, never a real account credential.
  const enrollment = { challenge_token: "qr-ui-fixture", manual_key: "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", otpauth_uri: "otpauth://totp/PlatformaCRM:test%40example.com?secret=GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ&issuer=PlatformaCRM", issuer: "PlatformaCRM", account: "test@example.com", expires_at: new Date(Date.now() + 300000).toISOString() };
  await page.route("**/api/auth/token/", route => route.fulfill({ status: 202, json: { code: "mfa_enrollment_required", challenge_token: enrollment.challenge_token, method: "totp", expires_at: enrollment.expires_at } }));
  await page.route("**/api/auth/mfa/enrollment/start/", route => route.fulfill({ json: enrollment }));
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("test@example.com");
  await page.locator('form input[type="password"]').fill("Fixture-password-123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/mfa/);
  await expect(page.getByTestId("authenticator-qr")).toBeVisible();
  await expect(page.locator('a[href^="otpauth:"]')).toHaveCount(0);
  const fieldBounds = await page.getByLabel("Код подтверждения").boundingBox();
  const qrBounds = await page.getByTestId("authenticator-qr").boundingBox();
  expect(fieldBounds!.width).toBeLessThanOrEqual(200);
  expect(Math.abs(fieldBounds!.x + fieldBounds!.width / 2 - qrBounds!.x - qrBounds!.width / 2)).toBeLessThan(2);
  await expect(page.locator("code")).toBeHidden();
  await page.getByText("Не удаётся отсканировать?", { exact: true }).click();
  await expect(page.locator("code")).toHaveText(enrollment.manual_key);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
