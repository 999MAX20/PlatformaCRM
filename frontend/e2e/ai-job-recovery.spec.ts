import { expect, test, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
}

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires an isolated account");
});

test("failed queued AI answer permits an explicit new request and displays its sources", async ({ page }) => {
  const requests: { idempotency_key: string }[] = [];
  await page.route("**/api/ai/assistant/chat/", route => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({ status: 202, json: { job: {
      id: requests.length, status: requests.length === 1 ? "failed" : "succeeded",
      result_json: { answer: "Synthetic recovery answer", sources: [{ id: "CRM-summary", label: "CRM" }], provider_state: "live", is_mock: false },
    } } });
  });
  await login(page);
  await page.goto("/app/ai-assistant");
  const refresh = page.getByRole("button", { name: "Обновить сводку", exact: true });
  await refresh.click();
  await expect(page.getByText("Ответ ИИ недоступен или не прошёл проверку. Повторите запрос или продолжите работу вручную.", { exact: true })).toBeVisible();
  await refresh.click();
  await expect(page.getByText("Synthetic recovery answer", { exact: true })).toBeVisible();
  await expect(page.getByText("CRM [CRM-summary]", { exact: true })).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[0].idempotency_key).not.toBe(requests[1].idempotency_key);
});

test("an AI polling loop stops before reading again after logout", async ({ page }) => {
  let polls = 0;
  await page.route("**/api/ai/assistant/chat/", route => route.fulfill({ status: 202, json: { job: { id: 999999, status: "running", result_json: {} } } }));
  await page.route("**/api/ai/jobs/999999/", route => {
    polls++;
    return route.fulfill({ json: { id: 999999, status: "running", result_json: {} } });
  });
  await login(page);
  await page.getByTestId("header-account-link").click();
  await expect(page.getByTestId("merchant-logout")).toBeVisible();
  const queued = page.waitForResponse(response => response.url().endsWith("/api/ai/assistant/chat/"));
  await page.evaluate(async () => {
    const modulePath = "/src/api/ai.ts";
    const { aiApi } = await import(modulePath);
    Reflect.set(window, "queuedOutcome", "pending");
    void aiApi.assistantChat({ business: 1, message: "Synthetic pending answer" }).then(
      () => Reflect.set(window, "queuedOutcome", "resolved"),
      () => Reflect.set(window, "queuedOutcome", "rejected"),
    );
  });
  await queued;
  await page.getByTestId("merchant-logout").click();
  await expect(page).toHaveURL(/\/login/);
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "queuedOutcome")), { timeout: 6000 }).toBe("rejected");
  expect(polls).toBe(0);
});
