import { expect, test } from "@playwright/test";
import { resetAccountPreferences } from "./support/account-preferences";

test.afterEach(async ({ request }) => resetAccountPreferences(request));

test("personal language saves independently and survives reload with recovery", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  const profile = page.locator("#profile");
  const settings = page.locator("#interface");
  const name = profile.locator('input[autocomplete="name"]');
  const originalName = await name.inputValue();
  await name.fill("Unsaved profile draft");
  await expect(profile.getByRole("combobox")).toHaveCount(0);
  await settings.getByRole("combobox").first().click();
  await page.getByRole("option", { name: "English", exact: true }).click();
  const failedRoute = "**/api/auth/me/";
  await page.route(failedRoute, async route => {
    if (route.request().method() === "PATCH") await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Settings temporarily unavailable" }) });
    else await route.continue();
  });
  await settings.locator('button[type="submit"]').click();
  await expect(settings.getByRole("alert")).toBeVisible();
  await expect(settings.getByRole("heading")).toHaveText("Интерфейс");
  await expect(name).toHaveValue("Unsaved profile draft");
  await page.unroute(failedRoute);
  const saved = page.waitForResponse(response => response.url().endsWith("/api/auth/me/") && response.request().method() === "PATCH");
  await settings.locator('button[type="submit"]').click();
  const response = await saved;
  expect(response.ok()).toBeTruthy();
  expect(response.request().postDataJSON()).toEqual({ preferences: { language: "en", start_page: "dashboard" } });
  await expect(settings.getByRole("heading")).toHaveText("Interface");
  await expect(name).toHaveValue("Unsaved profile draft");
  await page.reload();
  await expect(settings.getByRole("heading")).toHaveText("Interface");
  await expect(name).toHaveValue(originalName);
  await settings.getByRole("combobox").first().click();
  await page.getByRole("option", { name: "Русский", exact: true }).click();
  await settings.locator('button[type="submit"]').click();
  await expect(settings.getByRole("heading")).toHaveText("Интерфейс");
  await expect(settings.locator('button[type="submit"]')).toBeDisabled();
  await page.screenshot({ path: `../output/account-settings-${testInfo.project.name}.png`, fullPage: true });
});
