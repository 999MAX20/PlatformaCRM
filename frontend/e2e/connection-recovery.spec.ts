import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable session fixtures");
});

test("returning to a visible tab resumes a missed startup recovery", async ({ page }) => {
  await crmSession(page);
  await page.route("**/api/auth/me/", route => route.fulfill({ status: 503, json: { detail: "Temporary outage" } }));
  await page.reload();
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  await page.clock.install();
  await page.evaluate(() => Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" }));
  await page.clock.fastForward(65_000);
  await page.unroute("**/api/auth/me/");
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(page.getByTestId("session-recovery")).toBeHidden({ timeout: 3_000 });
  await expect(page.getByTestId("header-account-link")).toBeVisible();
});

test("successful service retry also resumes session recovery without losing the draft", async ({ page }) => {
  await crmSession(page);
  await page.goto("/app/account");
  const draft = page.locator('input[autocomplete="name"]');
  await draft.fill("Connection recovery draft");
  await page.route("**/ready/", route => route.fulfill({ status: 503, json: { status: "degraded" } }));
  await page.route("**/api/auth/token/refresh/", route => route.abort("internetdisconnected"));
  await page.evaluate(async () => {
    const clientPath = "/src/api/client.ts";
    const tokenPath = "/src/api/token.ts";
    try { await (await import(tokenPath)).refreshToken(); }
    catch (error) { (await import(clientPath)).handleSessionRecoveryError(error); }
    window.dispatchEvent(new Event("online"));
  });
  const banner = page.getByTestId("connectivity-banner");
  await expect(banner.getByRole("button", { name: "Повторить", exact: true })).toBeVisible();
  await expect(page.getByTestId("session-recovery")).toBeVisible();
  await page.unroute("**/ready/");
  await page.unroute("**/api/auth/token/refresh/");
  await banner.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(banner).toBeHidden();
  await expect(page.getByTestId("session-recovery")).toBeHidden({ timeout: 3_000 });
  await expect(draft).toHaveValue("Connection recovery draft");
});
