import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/e2e/fixtures/state-behavior.html");
  await expect(page.getByTestId("draft")).toBeVisible();
});

test("one request produces one toast and keyboard focus pauses expiration", async ({ page }) => {
  await page.getByTestId("duplicate").click();
  await expect(page.getByTestId("action-feedback")).toHaveCount(1);
  await page.getByTestId("action-feedback").getByRole("button", { name: "Закрыть" }).click();
  await page.getByTestId("short-toast").click();
  const close = page.getByTestId("action-feedback").getByRole("button", { name: "Закрыть" });
  await close.focus();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(1300);
  await expect(close).toBeVisible();
  await page.getByTestId("draft").focus();
  await expect(page.getByTestId("action-feedback")).toHaveCount(0);
});

test("inline and toast retry wait for the server delay without expiring the action", async ({ page }) => {
  await page.getByTestId("rate").click();
  const retry = page.getByTestId("inline-fallback").filter({ hasText: "Слишком много попыток" }).getByRole("button");
  await expect(retry).toBeDisabled();
  await expect(retry).toHaveText(/Повторить через/);
  await expect(retry).toBeEnabled();
  await retry.click();
  await expect(page.getByTestId("counts")).toHaveText("1,0,0");
  await page.getByTestId("rate-toast").click();
  const action = page.getByTestId("action-feedback-action");
  await expect(action).toBeDisabled();
  await page.waitForTimeout(1200);
  await expect(action).toBeVisible();
  await expect(action).toBeEnabled();
  await action.click();
  await expect(page.getByTestId("counts")).toHaveText("2,0,0");
});

test("failed undo unlocks feedback and offers a read instead of repeating the mutation", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.getByTestId("undo-failure").click();
  await page.getByTestId("action-feedback-action").click();
  const feedback = page.getByTestId("action-feedback");
  await expect(feedback).toContainText("Не удалось подтвердить отмену");
  await expect(feedback.getByRole("button", { name: "Отменить", exact: true })).toHaveCount(0);
  await expect(page.getByTestId("action-feedback-action")).toBeEnabled();
  await page.getByTestId("action-feedback-action").click();
  await expect(feedback).toHaveCount(0);
  await expect(page.getByTestId("counts")).toHaveText("0,1,1");
  expect(errors).toEqual([]);
});

test("finishing an earlier undo does not dismiss a newer operation", async ({ page }) => {
  await page.getByTestId("undo-pending").click();
  await page.getByTestId("action-feedback-action").click();
  await page.getByTestId("undo-new").click();
  await page.getByTestId("finish-old").click();
  await expect(page.getByTestId("action-feedback")).toContainText("New operation");
  await expect(page.getByTestId("action-feedback-action")).toBeEnabled();
});

test("support details are meaningful, copyable, and absent for a normal denial", async ({ page }) => {
  await expect(page.getByTestId("permission-case").getByTestId("recovery-details")).toHaveCount(0);
  const support = page.getByTestId("support-case");
  await expect(support).not.toContainText("SQLSTATE");
  await support.locator("summary").click();
  await expect(support).toContainText("Обращение автоматически не создаётся");
  await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (text: string) => sessionStorage.setItem("copied-code", text) } }));
  await support.getByRole("button", { name: "Копировать", exact: true }).click();
  expect(await page.evaluate(() => sessionStorage.getItem("copied-code"))).toBe("test-internal");
  await expect(support.getByRole("button", { name: "Копировать", exact: true })).toHaveText("Скопировано");
  await page.evaluate(() => Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async () => { throw new Error("Denied"); } } }));
  await support.getByRole("button", { name: "Копировать", exact: true }).click();
  await expect(support).toContainText("скопируйте его вручную");
});

test("reconnect waits for the app, keeps drafts and survives a failed probe", async ({ page, context }) => {
  let release: () => void = () => undefined;
  const pending = new Promise<void>(resolve => { release = resolve; });
  let attempts = 0;
  await page.route("**/health/", async route => {
    attempts++;
    if (attempts === 1) await pending;
    await route.fulfill({ status: attempts === 1 ? 503 : 200, json: { status: "ok" } });
  });
  await page.getByTestId("draft").fill("Unsaved draft");
  await context.setOffline(true);
  await expect(page.getByTestId("connectivity-banner")).toContainText("Нет соединения");
  await context.setOffline(false);
  await expect(page.getByTestId("connectivity-banner")).toContainText("Восстанавливаем соединение");
  await page.waitForTimeout(1700);
  await expect(page.getByTestId("connectivity-banner")).toBeVisible();
  release();
  await expect(page.getByTestId("connectivity-banner")).toContainText("пока не восстановлена");
  await page.getByTestId("connectivity-banner").getByRole("button", { name: "Повторить" }).click();
  await expect(page.getByTestId("connectivity-banner")).toHaveCount(0);
  await expect(page.getByTestId("draft")).toHaveValue("Unsaved draft");
  await expect(page.getByTestId("reads")).toHaveText("2");
  expect(attempts).toBe(2);
});
