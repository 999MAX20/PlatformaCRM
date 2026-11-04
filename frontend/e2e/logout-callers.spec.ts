import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
test.beforeEach(() => test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Isolated fixture only"));
test("platform menu waits for logout and exposes failed revocation", async ({ page }) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("platform_admin@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/platform/);
  await page.route("**/api/auth/logout/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  await page.getByRole("button", { name: /^Мой аккаунт:/ }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await expect(page.getByTestId("logout-status")).toContainText("Не удалось завершить выход");
  await expect(page).toHaveURL(/\/platform/);
  await page.unroute("**/api/auth/logout/");
  await page.getByTestId("logout-status").getByRole("button").click();
  await expect(page).toHaveURL(/\/login/);
});
test("wrong-account invitation retains sign-out failure and supports retry", async ({ page }) => {
  await crmSession(page);
  await page.route("**/api/team/invitations/preview/synthetic-logout/", route => route.fulfill({ json: {
    business_name: "Synthetic invitation", email: "other@example.invalid", full_name: "Other", role: "manager", status: "pending", requires_authentication: true,
  } }));
  await page.goto("/invite/synthetic-logout");
  await page.route("**/api/auth/logout/", route => route.abort("internetdisconnected"));
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page.getByTestId("logout-status")).toContainText("Не удалось завершить выход");
  await expect(page.getByRole("button", { name: "Выйти", exact: true })).toBeVisible();
  await page.unroute("**/api/auth/logout/");
  await page.getByTestId("logout-status").getByRole("button").click();
  await expect(page.getByRole("button", { name: "Выйти", exact: true })).toBeHidden();
  await expect(page.getByTestId("logout-status")).toBeHidden();
});
