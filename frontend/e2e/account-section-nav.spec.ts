import { expect, test } from "@playwright/test";

test("account section navigation follows clicks, manual scroll and keyboard", async ({ page }, testInfo) => {
  if (testInfo.project.name === "desktop-chromium") await page.setViewportSize({ width: 1920, height: 720 });
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
  const nav = page.getByRole("navigation", { name: "Разделы аккаунта" });
  const profile = nav.getByRole("link", { name: "Профиль", exact: true });
  const security = nav.getByRole("link", { name: "Безопасность", exact: true });
  const notifications = nav.getByRole("link", { name: "Личные уведомления", exact: true });
  await expect(profile).toHaveAttribute("aria-current", "location");
  await nav.getByRole("link", { name: "Интерфейс", exact: true }).click();
  await expect(nav.locator('[href="#interface"]')).toHaveAttribute("aria-current", "location");
  await security.click();
  await expect(security).toHaveAttribute("aria-current", "location");
  await expect(nav.locator('[aria-current="location"]')).toHaveCount(1);
  await notifications.click();
  await expect(notifications).toHaveAttribute("aria-current", "location");
  await expect(nav).toBeInViewport();
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(profile).toHaveAttribute("aria-current", "location");
  await page.evaluate(() => window.scrollTo(0, document.getElementById("security")!.getBoundingClientRect().top + scrollY - (innerWidth >= 1280 ? 96 : 144)));
  await expect(security).toHaveAttribute("aria-current", "location");
  await profile.focus();
  await page.keyboard.press("Enter");
  await expect(profile).toHaveAttribute("aria-current", "location");
  const viewport = page.viewportSize()!;
  await page.setViewportSize({ width: viewport.width, height: viewport.height - 80 });
  await security.click();
  await expect(security).toHaveAttribute("aria-current", "location");
  await expect(nav).toBeInViewport();
  await profile.click();
  await page.setViewportSize(viewport);
  await expect(profile).toHaveAttribute("aria-current", "location");
  const navBox = (await nav.boundingBox())!;
  const profileBox = (await page.locator("#profile").boundingBox())!;
  const globalWidth = viewport.width >= 1024 ? 64 : 0;
  expect(Math.abs(profileBox.x - globalWidth - (viewport.width - profileBox.x - profileBox.width))).toBeLessThan(2);
  if (viewport.width >= 1280) {
    expect(navBox.x + navBox.width).toBeLessThan(profileBox.x);
    expect(Math.abs(navBox.x + navBox.width / 2 - (globalWidth + profileBox.x) / 2)).toBeLessThan(2);
    expect(profileBox.width).toBe(960);
  }
  else expect(navBox.y).toBeLessThan(profileBox.y);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: `../output/account-nav-${test.info().project.name}.png`, fullPage: true });
  if (viewport.width >= 1280) {
    await page.setViewportSize({ width: 1280, height: 720 });
    const compactNav = (await nav.boundingBox())!;
    const compactProfile = (await page.locator("#profile").boundingBox())!;
    expect(compactProfile.width).toBe(960);
    expect(Math.abs(compactNav.x + compactNav.width / 2 - (64 + compactProfile.x) / 2)).toBeLessThan(2);
    await notifications.click();
    await expect(nav).toBeInViewport();
  }
});
