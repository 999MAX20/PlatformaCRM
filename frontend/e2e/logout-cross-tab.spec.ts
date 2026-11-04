import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
test("another tab completes logout and removes an earlier failure notice", async ({ page, context }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Isolated fixture only");
  await crmSession(page); await page.goto("/app/account");
  const sibling = await context.newPage(); await sibling.goto("/app/account");
  await expect(sibling.getByTestId("merchant-logout")).toBeVisible();
  await page.route("**/api/auth/logout/", route => route.fulfill({ status: 503, json: { detail: "Synthetic unavailable" } }));
  await page.getByTestId("merchant-logout").click();
  await expect(page.getByTestId("logout-status")).toContainText("Не удалось завершить выход");
  await sibling.getByTestId("merchant-logout").click();
  await expect(sibling).toHaveURL(/\/login/);
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByTestId("logout-status")).toBeHidden();
  await page.reload(); await expect(page.locator('form input[type="password"]')).toBeVisible();
});
