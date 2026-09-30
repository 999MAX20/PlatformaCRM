import { expect, test } from "@playwright/test";

test("search stays half the profile width across routes, focus and sidebar states", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  const profile = page.locator("main section").filter({ has: page.getByRole("heading", { name: "Профиль", exact: true }) });
  await expect(profile).toBeVisible();
  const profileBounds = (await profile.boundingBox())!;
  const desktop = page.viewportSize()!.width >= 1024;
  const input = page.locator('header input[aria-label="Поиск"]:visible');
  async function openSearch() {
    if (!desktop) await page.locator("header").getByRole("button", { name: "Поиск", exact: true }).click();
    await expect(input).toBeVisible();
  }
  async function checkWidth() {
    const box = (await input.locator("..").boundingBox())!;
    expect(Math.abs(box.width * 2 - profileBounds.width)).toBeLessThan(2);
    await expect(page.locator("header .lucide-command")).toHaveCount(0);
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width);
    return box;
  }
  await openSearch();
  const original = await checkWidth();
  await input.focus();
  await input.fill("test");
  expect((await checkWidth()).x).toBeCloseTo(original.x, 0);
  await input.fill("");
  if (desktop) {
    await page.getByTestId("desktop-sidebar").hover();
    await checkWidth();
    await page.mouse.move(page.viewportSize()!.width - 10, 100);
    await checkWidth();
  }
  await page.screenshot({ path: `../output/header-search-${test.info().project.name}.png`, fullPage: true });
  for (const route of ["dashboard", "leads", "clients", "deals", "calendar", "tasks", "settings"]) {
    await page.goto(`/app/${route}`);
    await openSearch();
    const box = await checkWidth();
    expect(box.x).toBeCloseTo(original.x, 0);
    await input.fill("test");
    await checkWidth();
    await input.fill("");
  }
});
