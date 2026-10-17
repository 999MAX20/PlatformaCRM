import { expect, test, type Page } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import type { Client, Lead } from "../src/types";

const leadList = (url: URL) => url.pathname === "/api/leads/";
const workspace = (page: Page) => page.getByTestId("leads-workspace-ready");
const records = (page: Page) => page.evaluate(() =>
  Object.keys(localStorage).filter(key => key.startsWith("platforma:leads:v1:"))
    .map(key => ({ key, value: JSON.parse(localStorage.getItem(key)!) })));

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires disposable tenant fixtures");
});

async function seedAndCache(page: Page) {
  const session = await crmSession(page);
  const marker = `AUD01-private-${Date.now()}`;
  const client = await session.create<Client>("clients", { full_name: marker, source: "manual" });
  const lead = await session.create<Lead>("leads", { client: client.id, message: marker, source: "manual", responsible_user: session.userId });
  await page.goto("/app/leads");
  await expect(workspace(page)).toContainText(marker);
  await expect.poll(async () => JSON.stringify(await records(page))).toContain(marker);
  return { ...session, marker, lead };
}

async function logout(page: Page) {
  await page.getByTestId("header-account-link").click();
  const response = page.waitForResponse(r => r.url().endsWith("/api/auth/logout/"));
  await page.getByTestId("merchant-logout").click();
  await response;
  await expect(page).toHaveURL(/\/login/);
}

test("A logout then empty B offline never displays or retains A's private leads", async ({ page, context }) => {
  const { marker, lead } = await seedAndCache(page);
  await page.evaluate(({ lead }) => {
    // Upgrade from the leaking legacy version must not adopt ownerless records.
    localStorage.setItem("zani_leads_cache", JSON.stringify([lead]));
    localStorage.setItem("zani_leads_offline_queue", JSON.stringify([{ id: "old", type: "note", leadId: lead.id, text: "private", createdAt: "" }]));
    Reflect.set(window, "sameDocument", true);
  }, { lead });
  await logout(page);
  expect(await records(page)).toEqual([]);
  expect(await page.evaluate(() => localStorage.getItem("zani_leads_cache"))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem("zani_leads_offline_queue"))).toBeNull();
  const mutationRequests: string[] = [];
  page.on("request", request => {
    if (request.method() === "POST" && /add-note|\/api\/tasks\//.test(request.url())) mutationRequests.push(request.url());
  });
  await page.locator('form input[type="email"]').fill("foreign_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  expect(await page.evaluate(() => Reflect.get(window, "sameDocument"))).toBe(true);
  await page.route(leadList, route => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await page.locator('a[href="/app/leads"]:visible').first().click();
  await expect(workspace(page)).toBeVisible();
  await context.setOffline(true);
  await expect(workspace(page)).not.toContainText(marker);
  expect(JSON.stringify(await records(page))).not.toContain(marker);
  expect(mutationRequests).toEqual([]);
  await context.setOffline(false);
});

for (const failure of ["temporary error", "connection loss"]) test(`same session keeps offline fallback through ${failure} and reconnects`, async ({ page, context }) => {
  const { marker } = await seedAndCache(page);
  await page.route(leadList, route => failure === "connection loss"
    ? route.abort("internetdisconnected")
    : route.fulfill({ status: 503, json: { detail: "Temporary outage" } }));
  await page.reload();
  await expect(workspace(page)).toBeVisible();
  // A fresh document has no React Query rows; this exercises persisted fallback.
  await context.setOffline(true);
  await expect(workspace(page)).toContainText(marker);
  await page.unroute(leadList);
  await context.setOffline(false);
  await expect(workspace(page)).toContainText(marker);
  await expect.poll(async () => JSON.stringify(await records(page))).toContain(marker);
});

for (const status of [200, 403]) test(`fresh ${status === 200 ? "empty response" : "permission denial"} removes stale offline rows`, async ({ page, context }) => {
  const { marker } = await seedAndCache(page);
  await page.route(leadList, route => route.fulfill({
    status,
    json: status === 200 ? { count: 0, next: null, previous: null, results: [] } : { detail: "Forbidden" },
  }));
  await page.reload();
  await expect(workspace(page)).toBeVisible();
  await expect.poll(async () => JSON.stringify(await records(page))).not.toContain(marker);
  await context.setOffline(true);
  await expect(workspace(page)).not.toContainText(marker);
  await context.setOffline(false);
});

test("session expiration clears sensitive storage without requiring a manual logout", async ({ page }) => {
  await seedAndCache(page);
  await page.evaluate(async () => {
    const clientPath = "/src/api/client.ts";
    (await import(clientPath)).expireBrowserSession();
  });
  await expect(page).toHaveURL(/\/login/);
  expect(await records(page)).toEqual([]);
});

test("loading does not erase the authorized snapshot before the empty response arrives", async ({ page }) => {
  const { marker } = await seedAndCache(page);
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route(leadList, async route => {
    await pending;
    await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
  });
  await page.reload();
  await expect(page.getByTestId("header-account-link")).toBeVisible();
  expect(JSON.stringify(await records(page))).toContain(marker);
  release();
  await expect(workspace(page)).toBeVisible();
  await expect.poll(async () => JSON.stringify(await records(page))).not.toContain(marker);
});
