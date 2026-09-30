import { expect, test, type Page } from "@playwright/test";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";

async function savedAction(page: Page, path: string, action: () => Promise<void>) {
  const response = page.waitForResponse(item => item.request().method() === "POST" && new URL(item.url()).pathname === path);
  await action();
  const result = await response;
  expect(result.ok(), await result.text()).toBeTruthy();
  return result.json();
}

test("manager creates a client and completes its linked lead-to-deal cycle entirely in UI", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires isolated synthetic CRM data");
  test.setTimeout(90_000);
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("business_manager@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  const login = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith("/api/auth/token/"));
  await page.locator('form button[type="submit"]').click();
  const credentials = await login;
  expect(credentials.ok()).toBeTruthy();
  const headers = { Authorization: `Bearer ${(await credentials.json()).access}` };
  await expect(page.getByTestId("header-account-link")).toBeVisible();

  const marker = `Staff cycle ${Date.now()}`;
  await page.goto("/app/clients");
  await page.locator('[data-testid="page-primary-action"]:visible').click();
  const form = page.getByTestId("client-action-form");
  await form.locator('input[name="full_name"]').fill(marker);
  await form.locator('input[name="email"]').fill(`staff-${Date.now()}@example.invalid`);
  const client = await savedAction(page, "/api/clients/", () => form.getByTestId("client-action-submit").click());
  await expect(page.getByTestId("crm-entity-drawer")).toBeVisible();
  await page.goto(`/app/clients/${client.id}`);
  await page.locator('[data-crm-action-id="create_lead"]').click();
  const leadForm = page.getByRole("dialog");
  await leadForm.locator("textarea").fill(`${marker} consultation`);
  const lead = await savedAction(page, "/api/leads/", () => leadForm.getByTestId("lead-action-submit").click());
  expect(lead.client).toBe(client.id);
  expect(lead.business).toBe(client.business);

  await page.goto(`/app/leads/${lead.id}`);
  await savedAction(page, `/api/leads/${lead.id}/mark-contacted/`, () => page.locator('[data-crm-action-id="contacted"]').click());
  const deal = await savedAction(page, `/api/leads/${lead.id}/create-deal/`, () => page.locator('[data-crm-action-id="create_deal"]').click());
  expect(deal.client).toBe(client.id);
  expect(deal.lead).toBe(lead.id);
  expect(deal.business).toBe(client.business);

  await page.goto(`/app/deals/${deal.id}`);
  await savedAction(page, `/api/deals/${deal.id}/mark-won/`, async () => {
    await page.locator('[data-crm-action-id="won"]').click();
    await page.getByRole("dialog").getByRole("button", { name: "Подтвердить", exact: true }).click();
  });
  await page.reload();
  await expect(page.locator('[data-crm-action-id="reopen"]')).toBeVisible();
  const persisted = await page.request.get(`${api}/api/deals/${deal.id}/`, { headers });
  expect(persisted.ok()).toBeTruthy();
  expect(await persisted.json()).toMatchObject({ client: client.id, lead: lead.id, business: client.business, status: "won" });
  const cardResponse = await page.request.get(`${api}/api/clients/${client.id}/crm-card/`, { headers });
  expect(cardResponse.ok()).toBeTruthy();
  const card = await cardResponse.json();
  expect(card.leads.some((item: { id: number }) => item.id === lead.id)).toBe(true);
  expect(card.deals.some((item: { id: number; status: string }) => item.id === deal.id && item.status === "won")).toBe(true);
  expect(card.timeline.length).toBeGreaterThan(0);
});
