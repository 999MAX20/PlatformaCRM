import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";
import jsQR from "jsqr";
import { PNG } from "pngjs";

// Independent decoder and RFC 6238 generator verify the displayed QR, not its props.
function totp(secret: string, offset = 0) {
  const bits = [...secret].map(c => "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".indexOf(c).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from(bits.match(/.{8}/g)!.map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offset));
  const digest = createHmac("sha1", key).update(counter).digest();
  return ((digest.readUInt32BE(digest[19] & 15) & 0x7fffffff) % 1000000).toString().padStart(6, "0");
}

test("scan QR, reject bad code, enroll and sign in with TOTP", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Mutates only isolated seeded accounts");
  const email = process.env.E2E_OWNER_EMAIL || "business_owner@example.com";
  const password = process.env.E2E_PASSWORD || "ZaniTest123!";
  const external: string[] = [];
  page.on("request", request => { if (!new URL(request.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/)) external.push(request.url()); });
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  const startResponse = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/start/"));
  await page.getByRole("button", { name: "Подключить MFA", exact: true }).click();
  const enrollment = await (await startResponse).json();
  const dialog = page.getByRole("dialog");
  const qr = dialog.getByRole("img", { name: "QR-код для Google Authenticator" });
  await expect(qr).toBeVisible();
  const png = PNG.sync.read(await qr.screenshot());
  const decoded = jsQR(new Uint8ClampedArray(png.data), png.width, png.height);
  expect(decoded?.data).toBe(enrollment.otpauth_uri);
  const uri = new URL(decoded!.data);
  expect(uri.protocol).toBe("otpauth:");
  expect(uri.hostname).toBe("totp");
  expect(uri.searchParams.get("issuer")).toBe("PlatformaCRM");
  const secret = uri.searchParams.get("secret")!;
  await expect(dialog.locator("code")).toBeHidden();
  await dialog.getByText("Не удаётся отсканировать?", { exact: true }).click();
  await expect(dialog.locator("code")).toHaveText(secret);
  const qrCenter = await qr.boundingBox();
  for (const element of [dialog.locator("summary"), dialog.locator("code"), dialog.getByRole("button", { name: "Подключить защиту" })]) {
    const bounds = (await element.boundingBox())!;
    expect(Math.abs(bounds.x + bounds.width / 2 - qrCenter!.x - qrCenter!.width / 2)).toBeLessThan(2);
  }
  await expect(dialog.getByRole("button", { name: "Отмена", exact: true })).toHaveCount(0);
  await page.screenshot({ path: `../output/account-qr-expanded-${test.info().project.name}.png`, fullPage: true });
  await dialog.getByText("Не удаётся отсканировать?", { exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: `../output/account-qr-${test.info().project.name}.png`, fullPage: true });
  const input = dialog.getByLabel("Код подтверждения");
  await expect(dialog.locator('a[href^="otpauth:"]')).toHaveCount(0);
  const fieldBounds = await input.boundingBox();
  const qrBounds = await qr.boundingBox();
  expect(fieldBounds!.width).toBeLessThanOrEqual(200);
  expect(Math.abs(fieldBounds!.x + fieldBounds!.width / 2 - qrBounds!.x - qrBounds!.width / 2)).toBeLessThan(2);
  let badCode = "000000";
  while ([-1, 0, 1].some(offset => totp(secret, offset) === badCode)) badCode = String(Number(badCode) + 1).padStart(6, "0");
  await input.fill(badCode);
  const rejection = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/confirm/"));
  await dialog.getByRole("button", { name: "Подключить защиту" }).click();
  expect((await rejection).status()).toBe(401);
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(qr).toBeVisible();
  await input.fill(totp(secret));
  const confirmation = page.waitForResponse(r => r.url().endsWith("/mfa/enrollment/confirm/"));
  await dialog.getByRole("button", { name: "Подключить защиту" }).click();
  const confirmed = await (await confirmation).json();
  expect(confirmed.recovery_codes).toHaveLength(10);
  try {
    await expect(dialog.getByRole("button", { name: "Скопировать коды" })).toBeVisible();
    await expect(qr).toHaveCount(0);
    await dialog.getByRole("button", { name: "Закрыть", exact: true }).last().click();
    await expect(page.getByText("Защита включена", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Выйти", exact: true }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.locator('form input[type="email"]').fill(email);
    await page.locator('form input[type="password"]').fill(password);
    await page.locator('form button[type="submit"]').click();
    await expect(page).toHaveURL(/\/mfa/);
    await page.getByLabel("Код подтверждения").fill(totp(secret, 1));
    await page.getByRole("button", { name: "Подтвердить вход" }).click();
    await expect(page).toHaveURL(/\/app/);
    expect(external).toEqual([]);
  } finally {
    const login = await page.request.post("/api/auth/token/", { data: { email, password } });
    const pending = await login.json();
    const verified = await page.request.post("/api/auth/mfa/verify/", { data: { challenge_token: pending.challenge_token, code: confirmed.recovery_codes[0] } });
    const session = await verified.json();
    const disabled = await page.request.post("/api/auth/mfa/disable/", { headers: { Authorization: `Bearer ${session.access}` }, data: { password, code: confirmed.recovery_codes[1], reason: "Isolated QR test cleanup" } });
    expect(disabled.ok()).toBeTruthy();
  }
});
