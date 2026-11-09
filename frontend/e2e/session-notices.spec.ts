import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

for (const [language, width] of [["ru", 1440], ["kk", 390], ["en", 768]] as const) {
  test(`connection and session recovery share one notice area ${language}`, async ({ page }, info) => {
    test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Isolated fixture required");
    await page.setViewportSize({ width, height: 900 });
    const identity = await crmSession(page);
    const preference = await page.request.patch(`${process.env.E2E_API_BASE_URL}/api/auth/me/`, {
      headers: identity.headers, data: { preferences: { language } },
    });
    expect(preference.ok()).toBe(true);
    await page.evaluate(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/app/account");
    const name = page.locator('input[autocomplete="name"]');
    await expect(name).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", language);
    await name.fill("Preserved recovery draft");
    await page.route("**/ready/", route => route.fulfill({ status: 503, json: { status: "unavailable" } }));
    await page.route("**/api/auth/token/refresh/", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
    await page.route("**/api/tasks/999999/", route => route.fulfill({ status: 401, json: { detail: "Expired access" } }));
    await page.evaluate(async () => {
      const path = "/src/api/client.ts";
      await (await import(path)).apiClient.get("/api/tasks/999999/").catch(() => undefined);
      document.dispatchEvent(new Event("visibilitychange"));
    });
    const connection = page.getByTestId("connectivity-banner");
    const session = page.getByTestId("session-recovery");
    const host = page.getByTestId("notification-host");
    await expect(connection).toBeVisible();
    await expect(connection.locator("xpath=../..")).toHaveCSS("opacity", "1");
    await expect(session).toBeHidden();
    await expect(host).toHaveCount(1);
    await expect(host.getByTestId("connectivity-banner")).toBeVisible();
    await page.screenshot({ animations: "disabled", path: info.outputPath(`outage-${language}.png`) });
    await connection.locator("button.platforma-notice-close").click();
    await expect(connection).toBeHidden();
    await expect(session).toBeHidden();
    await page.unroute("**/ready/");
    await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
    await expect(host.getByTestId("session-recovery")).toBeVisible();
    await expect(connection).toBeHidden();
    await expect(name).toHaveValue("Preserved recovery draft");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ animations: "disabled", path: info.outputPath(`session-${language}.png`) });
    await page.unroute("**/api/auth/token/refresh/");
    await session.getByRole("button").first().focus();
    await page.keyboard.press("Enter");
    await expect(session).toBeHidden();
    await expect(name).toHaveValue("Preserved recovery draft");
    await expect(page.getByTestId("header-account-link")).toBeVisible();
  });
}
