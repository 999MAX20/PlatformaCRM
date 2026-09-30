import { expect, test, type Page } from "@playwright/test";

async function account(page: Page) {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(process.env.E2E_OWNER_EMAIL || "business_owner@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD || "ZaniTest123!");
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/app/);
  await page.goto("/app/account");
}

// Transport fixtures exercise UI; Django tests verify real scanning and auth.
test("avatar crop syncs account and header and can be removed", async ({ page }) => {
  let image: string | null = null;
  const png = "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";
  await page.route("**/api/auth/me/avatar/", async route => {
    if (route.request().method() === "POST") {
      expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
      expect(route.request().postDataBuffer()?.toString()).toContain('name="size"');
      image = `data:image/png;base64,${png}`;
    }
    if (route.request().method() === "DELETE") image = null;
    await route.fulfill({ json: { image } });
  });
  await account(page);
  await expect(page.getByRole("button", { name: "Загрузить фото", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Изменить фото", exact: true }).click();
  await page.getByLabel("Загрузить фото", { exact: true }).setInputFiles({ name: "avatar.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
  await page.getByLabel("Масштаб", { exact: true }).fill("2");
  const crop = page.getByTestId("avatar-crop-preview");
  const before = await crop.locator("img").getAttribute("style");
  const bounds = (await crop.boundingBox())!;
  expect(bounds.width / bounds.height).toBeCloseTo(1.5, 1);
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width / 2 + 35, bounds.y + bounds.height / 2 + 20, { steps: 5 });
  await page.mouse.up();
  await expect(crop.locator("img")).not.toHaveAttribute("style", before!);
  await crop.focus();
  await crop.press("ArrowLeft");
  await expect(page.getByLabel("По горизонтали", { exact: true })).toHaveCount(0);
  await page.screenshot({ path: `../output/avatar-crop-${test.info().project.name}.png` });
  await page.getByRole("dialog").getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByTestId("header-account-link").locator("img")).toHaveAttribute("src", `data:image/png;base64,${png}`);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/app/tasks");
  await expect(page.getByTestId("header-account-link").locator("img")).toBeVisible();
  await page.goto("/app/account");
  await expect(page.getByRole("button", { name: "Изменить фото", exact: true })).toBeVisible();
  await page.screenshot({ path: `../output/account-layout-${test.info().project.name}.png` });
  await page.getByRole("button", { name: "Изменить фото", exact: true }).click();
  await page.getByRole("button", { name: "Убрать фото", exact: true }).click();
  await expect(page.getByTestId("header-account-link").locator("img")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test("email change requires confirmation and updates security row", async ({ page }) => {
  let confirmed = false;
  let access = "";
  await page.route("**/api/auth/me/", async route => {
    access = route.request().headers()["authorization"]?.replace("Bearer ", "") || access;
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({ response, json: confirmed ? { ...data, email: "new-login@example.com" } : data });
  });
  await page.route("**/api/auth/change-email/request/", async route => {
    expect(route.request().postDataJSON().new_email).toBe("new-login@example.com");
    expect(route.request().postDataJSON().current_password).toBe("StrongPass123!");
    await route.fulfill({ json: { ok: true, expires_in: 600 } });
  });
  await page.route("**/api/auth/change-email/confirm/", async route => {
    expect(route.request().postDataJSON().code).toBe("123456");
    confirmed = true;
    await route.fulfill({ json: { ok: true, email: "new-login@example.com", access } });
  });
  await account(page);
  const security = page.locator("#security");
  await expect(security.getByText(process.env.E2E_OWNER_EMAIL || "business_owner@example.com", { exact: true })).toBeVisible();
  await security.getByRole("button", { name: "Изменить почту", exact: true }).click();
  await page.getByLabel("Новая почта", { exact: true }).fill("new-login@example.com");
  await page.getByLabel("Текущий пароль", { exact: true }).fill("StrongPass123!");
  await page.getByRole("button", { name: "Получить код", exact: true }).click();
  await expect(page.getByLabel("Код из письма")).toBeVisible();
  await expect(security.getByText(process.env.E2E_OWNER_EMAIL || "business_owner@example.com", { exact: true })).toBeVisible();
  await page.getByLabel("Код из письма").fill("123456");
  await page.getByRole("dialog").getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(security.getByText("new-login@example.com", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
