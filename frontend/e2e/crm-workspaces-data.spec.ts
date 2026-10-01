import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test("client sorting and quick-view counts agree with the scoped API", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1" || testInfo.project.name !== "desktop-chromium", "Disposable desktop data contract");
  const session = await crmSession(page);
  const marker = `Sort ${Date.now()}`;
  for (const suffix of ["Z", "A", "M"]) await session.create("clients", { full_name: `${marker} ${suffix}` });
  await page.goto("/app/clients");
  const workspace = page.getByTestId("clients-workspace-ready");
  await expect(workspace).toBeVisible();
  await workspace.getByTestId("clients-search-input").fill(marker);
  await expect(workspace.locator("tbody tr[role='row']")).toHaveCount(3);
  const header = workspace.getByRole("columnheader").getByRole("button", { name: "Клиент", exact: true });
  for (const ordering of ["full_name", "-full_name"]) {
    const response = page.waitForResponse(item => new URL(item.url()).pathname === "/api/clients/" && new URL(item.url()).searchParams.get("ordering") === ordering);
    await header.click();
    expect((await response).ok()).toBeTruthy();
    const direct = await session.read("clients", { q: marker, ordering });
    await expect.poll(() => workspace.locator("tbody tr[role='row']").allTextContents()).toEqual(expect.arrayContaining(direct.results.map((client: { full_name: string }) => expect.stringContaining(client.full_name))));
    const texts = await workspace.locator("tbody tr[role='row']").allTextContents();
    direct.results.forEach((client: { full_name: string }, index: number) => expect(texts[index]).toContain(client.full_name));
  }
  const { summary } = await session.read("clients", { q: marker });
  await expect(workspace.getByRole("button", { name: /^Все\s/ })).toContainText(String(summary.total));
});

test("manager CRM workspaces keep localized controls and avoid forbidden team lookups", async ({ page }, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1" || testInfo.project.name !== "desktop-chromium", "Disposable locale/role matrix");
  test.setTimeout(120_000);
  const denied: string[] = [];
  page.on("response", response => { if (response.status() === 403) denied.push(new URL(response.url()).pathname); });
  await crmSession(page, "business_manager@example.com");
  for (const language of ["ru", "kk", "en"]) {
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), language);
    for (const route of ["clients", "leads", "deals"]) {
      await page.goto(`/app/${route}`);
      const workspace = page.getByTestId(`${route}-workspace-ready`);
      await expect(workspace).toBeVisible();
      await expect(workspace.getByTestId(`${route}-search-input`)).toBeVisible();
      const text = await workspace.innerText();
      expect(text).not.toMatch(/\b(?:common|clients|leads|deals)\.[A-Za-z]+/);
      expect(text).not.toContain("undefined");
    }
  }
  expect(denied).toEqual([]);
});

test("manager can retry the deal board without requesting a forbidden team directory", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable manager recovery");
  const denied: string[] = [];
  await crmSession(page, "business_manager@example.com");
  page.on("response", response => { if (response.status() === 403) denied.push(new URL(response.url()).pathname); });
  let failing = true;
  await page.route(url => url.pathname === "/api/deals/board/", async route => {
    if (failing) await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
    else await route.continue();
  });
  await page.goto("/app/deals");
  const retry = page.getByRole("button", { name: "Повторить", exact: true });
  await expect(retry).toBeVisible();
  failing = false;
  await retry.click();
  await expect(page.getByTestId("deals-workspace-ready")).toBeVisible();
  expect(denied).toEqual([]);
});
