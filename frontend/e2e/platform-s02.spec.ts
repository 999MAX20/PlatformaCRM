import { createHmac } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.E2E_PLATFORM_S02 !== "1", "Run scripts/verify_platform_s02.py for disposable platform fixtures");
});

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

async function login(page: Page, email = "platform_admin@example.com") {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(email);
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const pending = page.waitForResponse(response => response.url().endsWith("/api/auth/token/") && response.request().method() === "POST");
  await page.locator('form button[type="submit"]').click();
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const token = await response.json();
  await expect(page).toHaveURL(/\/platform/);
  return { Authorization: `Bearer ${token.access}` };
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBeTruthy();
}

function totp(secret: string) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = secret.replace(/=+$/u, "").split("").map(char => alphabet.indexOf(char).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from((bits.match(/.{8}/g) || []).map(byte => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac("sha1", key).update(counter).digest();
  return String((digest.readUInt32BE(digest[digest.length - 1] & 15) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

test("platform search and pagination reach all businesses and preserve return context", async ({ page }, info) => {
  await login(page);
  await page.goto("/platform/merchants?search=S02%20Clinic&page_size=10");
  await expect(page.locator("tbody tr")).toHaveCount(10);
  await expect(page.getByTestId("crm-pagination")).toContainText("23");
  await page.getByRole("button", { name: ru["pagination.next"], exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.locator("tbody tr")).toHaveCount(10);
  await page.locator('tbody a[href^="/platform/merchants/"]').first().click();
  await expect(page.getByTestId("support-action-history")).toBeVisible();
  await expect(page.getByText(ru["platform.support.readOnly"])).toBeVisible();
  await page.locator("main").getByRole("link", { name: ru["platform.nav.merchants"], exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  const search = page.getByRole("textbox", { name: ru["platform.merchants.search"] });
  await search.fill("S02 Clinic 00");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await search.fill("No such clinic");
  await expect(page.getByText(ru["platform.merchants.emptyTitle"], { exact: true })).toBeVisible();
  await expect(search).toBeFocused();
  await search.fill("S02 Clinic");
  await expect(page.locator("tbody tr")).toHaveCount(10);
  await noOverflow(page);
  await page.screenshot({ path: info.outputPath("platform-merchants.png"), fullPage: true });
});

test("support note uses real grant and MFA, preserves failed draft, then appears in paginated history", async ({ page }, info) => {
  test.setTimeout(90_000);
  const email = `s02-support-${info.project.name}@example.com`;
  const headers = await login(page, email);
  const response = await page.request.get(`${api}/api/platform/merchants/?search=S02%20Support`, { headers });
  const business = (await response.json()).results[0];
  await page.goto(`/platform/merchants/${business.id}/`);
  await expect(page.getByTestId("support-action-form")).toBeVisible();
  const start = await page.request.post(`${api}/api/auth/mfa/enrollment/start/`, { headers, data: {} });
  expect(start.ok()).toBeTruthy();
  const enrollment = await start.json();
  const confirmed = await page.request.post(`${api}/api/auth/mfa/enrollment/confirm/`, { data: { challenge_token: enrollment.challenge_token, code: totp(enrollment.manual_key) } });
  expect(confirmed.ok()).toBeTruthy();
  const codes = (await confirmed.json()).recovery_codes as string[];
  // Enrollment rotates the authenticated session. Restore the new cookie-backed
  // session before exercising the support form, as the real enrollment UI does.
  await page.reload();
  await expect(page.getByTestId("support-action-form")).toBeVisible();
  const note = `S02 verified support ${info.project.name}`;
  const text = page.getByRole("textbox", { name: ru["platform.merchantDetail.notePlaceholder"] });
  await text.fill(note);
  await page.getByLabel(ru["mfa.codeLabel"]).fill("invalid-factor");
  const failed = page.waitForResponse(item => item.url().endsWith("/api/auth/mfa/step-up/") && item.request().method() === "POST");
  await page.getByRole("button", { name: ru["platform.merchantDetail.saveAction"] }).click();
  expect((await failed).ok()).toBeFalsy();
  await expect(text).toHaveValue(note);
  await page.getByLabel(ru["mfa.codeLabel"]).fill(codes[0]);
  const saved = page.waitForResponse(item => item.url().endsWith("/support-actions/") && item.request().method() === "POST");
  await page.getByRole("button", { name: ru["platform.merchantDetail.saveAction"] }).click();
  expect((await saved).status()).toBe(201);
  await expect(text).toHaveValue("");
  await expect(page.getByTestId("support-action-history")).toContainText(note);
  await page.getByRole("button", { name: ru["pagination.next"], exact: true }).click();
  await expect(page.getByTestId("support-action-history")).not.toContainText(note);
  await noOverflow(page);
  await page.screenshot({ path: info.outputPath("platform-support.png"), fullPage: true });
});

test("platform load recovery and localized operations remain reachable", async ({ page }, info) => {
  await login(page);
  await page.route("**/api/platform/merchants/?*", route => route.fulfill({ status: 503, json: { detail: "Temporary failure" } }));
  await page.goto("/platform/merchants?search=S02");
  await expect(page.getByText(ru["platform.merchants.error"], { exact: true })).toBeVisible();
  await page.unroute("**/api/platform/merchants/?*");
  await page.getByRole("button", { name: ru["platform.merchantDetail.refresh"], exact: true }).last().click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    await page.goto("/platform/operations");
    await expect(page.getByRole("heading", { name: copy["platform.operations.title"], exact: true })).toBeVisible();
    await expect(page.getByText(copy["platform.support.recoveryByClinic"])).toBeVisible();
    const refresh = page.getByRole("button", { name: copy["platform.merchantDetail.refresh"], exact: true });
    await refresh.focus();
    await expect(refresh).toBeFocused();
    await refresh.press("Enter");
    await noOverflow(page);
    await page.screenshot({ path: info.outputPath(`platform-operations-${language}.png`), fullPage: true });
  }
  await page.goto("/platform");
  await expect(page.getByTestId("platform-overview-ready")).toBeVisible();
  await noOverflow(page);
  await page.screenshot({ path: info.outputPath("platform-overview.png"), fullPage: true });
});
