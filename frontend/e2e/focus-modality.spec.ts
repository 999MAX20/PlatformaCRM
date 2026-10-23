import { expect, test, type Locator } from "@playwright/test";

const outline = (control: Locator) => control.evaluate(el => getComputedStyle(el).outlineStyle);

for (const locale of ["ru", "kk", "en"]) test(`login ${locale} keeps DOM focus and typing without a pointer ring, restores keyboard ring`, async ({ page }, testInfo) => {
  await page.addInitScript(language => localStorage.setItem("ai_smb_language", language), locale);
  await page.route("**/api/**", route => ["fetch", "xhr"].includes(route.request().resourceType())
    ? route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"Unauthenticated"}' }) : route.continue());
  await page.goto("/login");
  const input = page.locator('input[type="email"]');
  await input.click();
  await expect(input).toBeFocused();
  await expect.poll(() => outline(input)).toBe("none");
  await input.pressSequentially("focus@example.test");
  await expect(input).toHaveValue("focus@example.test");
  await expect.poll(() => outline(input)).toBe("none");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  await expect(input).toBeFocused();
  await expect.poll(() => outline(input)).toBe("solid");
  await input.click();
  await expect.poll(() => outline(input)).toBe("none");
  if (testInfo.project.name.startsWith("mobile")) {
    await input.tap();
    await expect.poll(() => outline(input)).toBe("none");
  }
  await page.screenshot({ path: testInfo.outputPath(`login-${locale}-pointer.png`) });
});

test("programmatic focus follows dialog, search and widget input modality", async ({ page }) => {
  await page.goto("/e2e/fixtures/focus-modality.html");
  const trigger = page.getByRole("button", { name: "Open dialog" });
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect.poll(() => outline(dialog.locator(":focus"))).toBe("none");
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveCSS("box-shadow", /rgb\(0, 122, 89\).*6px/);
  await page.keyboard.press("Enter");
  await expect(dialog).toBeVisible();
  await expect.poll(() => outline(dialog.locator(":focus"))).not.toBe("none");
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await expect(trigger).toBeFocused();
  const searchTrigger = page.getByRole("button", { name: /Search choice/ });
  await searchTrigger.click();
  const search = page.getByRole("listbox").getByRole("textbox");
  await expect(search).toBeFocused();
  await expect.poll(() => outline(search)).toBe("none");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Enter");
  await expect(search).toBeFocused();
  await expect.poll(() => outline(search)).toBe("solid");
  await page.keyboard.press("Escape");
  const language = page.locator(".platforma-language-selector").getByRole("combobox");
  await language.click();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  await expect(language).toBeFocused();
  await expect(page.locator(".platforma-language-selector")).toHaveCSS("box-shadow", /4px/);
  await page.locator(".platforma-bubble").click();
  const message = page.locator(".platforma-input").last();
  await expect(message).toBeFocused();
  await expect.poll(() => outline(message)).toBe("none");
  await message.pressSequentially("Hello");
  await expect.poll(() => outline(message)).toBe("none");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  await expect(message).toBeFocused();
  await expect.poll(() => outline(message)).toBe("solid");
});

test("shared controls preserve errors, pointer selection and keyboard navigation", async ({ page }) => {
  await page.goto("/e2e/fixtures/action-color-roles.html");
  for (const label of ["Editable field", "Notes", "Invalid field", "Select record", "Select radio"]) {
    const control = page.getByLabel(label);
    await control.click();
    await expect(control).toBeFocused();
    await expect.poll(() => outline(control)).toBe("none");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(control).toBeFocused();
    await expect.poll(() => outline(control)).toBe("solid");
  }
  await expect(page.getByLabel("Select record", { exact: true })).toBeChecked();
  await expect(page.getByLabel("Invalid field")).toHaveAttribute("aria-invalid", "true");
});
