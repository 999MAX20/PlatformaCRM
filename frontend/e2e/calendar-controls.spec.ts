import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/e2e/fixtures/calendar-controls.html");
  await expect(page.getByRole("heading", { name: "Calendar controls" })).toBeVisible();
});

test("single date commits to controlled input, bounds, keyboard and disabled state", async ({ page }) => {
  await expect(page.getByTestId("disabled").getByRole("button")).toBeDisabled();
  await expect(page.getByTestId("readonly").getByRole("button")).toBeDisabled();
  await page.getByTestId("day").getByRole("button").click();
  await expect(page.locator('[data-date="2026-11-01"]')).toBeDisabled();
  await expect(page.locator('[data-date="2026-11-04"]')).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("day-value")).toHaveText("2026-11-05");
  await expect(page.getByTestId("day").locator("input")).toHaveValue("2026-11-05");
  await expect(page.getByTestId("day").getByRole("button")).toBeFocused();
  await page.getByTestId("day").locator("input").fill("2026-11-07");
  await expect(page.getByTestId("day-value")).toHaveText("2026-11-07");
  await page.getByTestId("day").locator("input").press("Alt+ArrowDown");
  await expect(page.locator('[data-date="2026-11-07"]')).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("date time preserves time, rejects out of bounds, cancels and clears", async ({ page }) => {
  const trigger = page.getByTestId("datetime").getByRole("button");
  await trigger.click();
  const panel = page.getByRole("dialog");
  await panel.locator('[data-date="2026-11-06"]').click();
  await expect(panel.locator('input[type="time"]')).toHaveValue("14:35");
  await panel.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(page.getByTestId("datetime-value")).toHaveText("2026-11-04T14:35");
  await trigger.click();
  await panel.locator('[data-date="2026-11-10"]').click();
  await panel.locator('input[type="time"]').fill("19:00");
  await expect(panel.getByRole("button", { name: "Применить", exact: true })).toBeDisabled();
  await panel.locator('input[type="time"]').fill("16:20");
  await page.screenshot({ path: "../output/calendar-shared-20261103/datetime-desktop.png" });
  await panel.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("datetime-value")).toHaveText("2026-11-10T16:20");
  await trigger.click();
  await panel.getByRole("button", { name: "Очистить", exact: true }).click();
  await expect(page.getByTestId("datetime-value")).toBeEmpty();
  await trigger.click();
  await expect(panel.getByRole("button", { name: "Применить", exact: true })).toBeDisabled();
  await panel.locator('[data-date="2026-11-06"]').click();
  await panel.locator('input[type="time"]').fill("09:15");
  await panel.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("datetime-value")).toHaveText("2026-11-06T09:15");
});

test("range draft is atomic, cancel/outside discard and clear applies", async ({ page }) => {
  const trigger = page.getByRole("button", { name: /^Range/ });
  await trigger.click();
  const panel = page.getByRole("dialog", { name: "Range" });
  await panel.locator('[data-date="2026-11-08"]').click();
  await expect(panel.getByRole("button", { name: "Применить", exact: true })).toBeDisabled();
  await expect(page.getByTestId("range-value")).toHaveText("2026-11-04/2026-11-05");
  await panel.locator('[data-date="2026-11-06"]').click();
  await panel.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("range-value")).toHaveText("2026-11-06/2026-11-08");
  await trigger.click();
  await panel.locator('[data-date="2026-11-10"]').click();
  await page.getByTestId("outside").click();
  await expect(panel).toHaveCount(0);
  await expect(page.getByTestId("outside")).toBeFocused();
  await expect(page.getByTestId("range-value")).toHaveText("2026-11-06/2026-11-08");
  await trigger.click();
  await panel.getByRole("button", { name: "Очистить", exact: true }).click();
  await panel.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("range-value")).toHaveText("/");
});

test("registered form value, native required validation, reset and nested focus", async ({ page }) => {
  await page.getByRole("button", { name: "Open form", exact: true }).click();
  const form = page.getByRole("dialog", { name: "Form", exact: true });
  await form.getByRole("button", { name: /Открыть календарь: Registered date/ }).click();
  const panel = page.getByRole("dialog", { name: "Registered date", exact: true });
  await panel.locator('[data-date="2026-11-05"]').click();
  await form.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(page.getByTestId("submitted")).toHaveText("2026-11-05");
  await form.getByRole("button", { name: "Reset date", exact: true }).click();
  await expect(form.getByLabel("Registered date", { exact: true })).toHaveValue("2026-11-06");
  await form.getByRole("button", { name: /Открыть календарь: Registered date/ }).click();
  await expect(panel.locator('[data-date="2026-11-06"]')).toBeFocused();
  await page.screenshot({ path: "../output/calendar-shared-20261103/registered-dialog.png" });
  await panel.getByRole("combobox").first().click();
  await page.keyboard.press("Escape");
  await expect(panel).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(form).toBeVisible();
  await form.getByRole("button", { name: /Открыть календарь: Registered date/ }).click();
  await panel.getByRole("button", { name: "Отмена", exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(panel).toHaveCount(0);
  await expect(form.getByRole("button", { name: "Submit", exact: true })).toBeFocused();
  await form.getByLabel("Registered date", { exact: true }).fill("");
  expect(await form.getByLabel("Registered date", { exact: true }).evaluate((input: HTMLInputElement) => input.checkValidity())).toBe(false);
  await form.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(page.getByTestId("submitted")).toHaveText("2026-11-05");
});

test("320px panel fits and date constraints survive keyboard navigation", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 320, height: 720 });
  await page.getByTestId("day").getByRole("button").click();
  const panel = page.getByRole("dialog");
  await panel.locator('[data-date="2026-11-02"]').focus();
  await page.keyboard.press("ArrowLeft");
  await expect(panel.locator('[data-date="2026-11-02"]')).toBeFocused();
  const box = await panel.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(320);
  expect(box!.y + box!.height).toBeLessThanOrEqual(720);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const month = panel.getByRole("combobox").first();
  await month.click();
  await panel.getByRole("option", { name: "сентябрь", exact: true }).click();
  expect(await month.locator("span").first().evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  await month.click();
  await panel.getByRole("option", { name: "ноябрь", exact: true }).click();
  await page.screenshot({ path: "../output/calendar-shared-20261103/calendar-320.png" });
  const colors = await panel.locator('[data-date="2026-11-04"]').evaluate(element => ({ color: getComputedStyle(element).color, background: getComputedStyle(element).backgroundColor }));
  const luminance = (color: string) => {
    const values = color.match(/\d+/g)!.slice(0, 3).map(n => Number(n) / 255).map(n => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4);
    return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
  };
  const a = luminance(colors.color), b = luminance(colors.background);
  expect((Math.max(a, b) + .05) / (Math.min(a, b) + .05)).toBeGreaterThanOrEqual(4.5);
  await page.keyboard.press("Escape");
  expect(errors).toEqual([]);
});

test("field error remains associated and red on hover", async ({ page }) => {
  const field = page.getByTestId("date-error").locator("input");
  await expect(field).toHaveAttribute("aria-invalid", "true");
  const id = await field.getAttribute("aria-describedby");
  expect(await page.locator(`[id="${id}"]`).textContent()).toBe("Укажите корректную дату.");
  await field.hover();
  await expect(field).toHaveCSS("border-top-color", "rgb(163, 59, 53)");
});

test("calendar controls expose action and disabled cursors without enabling disabled dates", async ({ page }) => {
  await expect(page.getByTestId("day").getByRole("button")).toHaveCSS("cursor", "pointer");
  await expect(page.getByTestId("disabled").getByRole("button")).toHaveCSS("cursor", "not-allowed");
  await expect(page.getByRole("button", { name: /^Range/ })).toHaveCSS("cursor", "pointer");
  await expect(page.getByTestId("calendar-period-picker")).toHaveCSS("cursor", "pointer");
  await page.getByTestId("day").getByRole("button").click();
  const panel = page.getByRole("dialog");
  await expect(panel.locator('[data-date="2026-11-05"]')).toHaveCSS("cursor", "pointer");
  await expect(panel.locator('[data-date="2026-11-01"]')).toHaveCSS("cursor", "not-allowed");
  await panel.locator('[data-date="2026-11-01"]').dispatchEvent("click");
  await expect(page.getByTestId("day-value")).toHaveText("2026-11-04");
  await expect(panel.getByRole("combobox").first()).toHaveCSS("cursor", "pointer");
});

for (const [language, name] of [["en", "September"], ["kk", "желтоқсан"]]) test(`320px ${language}: full long month and year`, async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.getByRole("button", { name: language, exact: true }).click();
  await page.getByTestId("day").getByRole("button").click();
  const panel = page.getByRole("dialog");
  const month = panel.getByRole("combobox").first();
  await month.click();
  await panel.getByRole("option", { name, exact: true }).click();
  for (const control of await panel.getByRole("combobox").all()) {
    expect(await control.locator("span").first().evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  }
  await page.screenshot({ path: `../output/calendar-shared-20261103/${language}-320.png` });
});

test("CRM range inside filter dialog keeps draft until apply and Escape closes only calendar", async ({ page }) => {
  await page.getByRole("button", { name: "Open form", exact: true }).click();
  const form = page.getByRole("dialog", { name: "Form", exact: true });
  await form.getByRole("button", { name: /Дата создания/ }).click();
  const panel = page.getByRole("dialog", { name: "Дата создания", exact: true });
  await panel.locator('[data-date="2026-11-04"]').click();
  await panel.locator('[data-date="2026-11-06"]').click();
  await expect(page.getByTestId("filters")).toHaveText("/");
  await panel.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("filters")).toHaveText("2026-11-04/2026-11-06");
  await form.getByRole("button", { name: /Дата создания/ }).click();
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(form).toBeVisible();
});

test("schedule day picker applies immediately and Records retains draft flow", async ({ page }) => {
  await page.getByTestId("calendar-period-picker").click();
  await page.getByTestId("calendar-date-picker").locator('[data-date="2026-11-06"]').click();
  await expect(page.getByTestId("day-value")).toHaveText("2026-11-06");
  await expect(page.getByTestId("calendar-date-picker")).toHaveCount(0);
  await page.getByTestId("records-trigger").click();
  await page.locator('#records-period-panel [data-date="2026-11-07"]').click();
  await page.locator('#records-period-panel [data-date="2026-11-08"]').click();
  await page.locator("#records-period-panel").getByRole("button", { name: "Применить", exact: true }).click();
  await expect(page.getByTestId("range-value")).toHaveText("2026-11-07/2026-11-08");
});

test("operations disallows future and periods over 365 days", async ({ page }) => {
  await page.getByTestId("operations-trigger").click();
  const panel = page.getByRole("dialog", { name: "Operations", exact: true });
  await expect(panel.locator('[data-date="2026-11-11"]')).toBeDisabled();
  await panel.locator('[data-date="2026-11-04"]').click();
  await panel.getByRole("combobox").nth(1).click();
  await panel.getByRole("option", { name: "2025", exact: true }).click();
  await panel.locator('[data-date="2025-11-01"]').click();
  await expect(panel.getByRole("button", { name: "Применить", exact: true })).toBeDisabled();
});

for (const language of ["ru", "kk", "en"]) test(`mobile ${language}: anchored overlay, full months, keyboard and no layout shift`, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: language, exact: true }).click();
  const marker = page.getByTestId("datetime");
  const before = await marker.boundingBox();
  await page.getByTestId("day").getByRole("button").click();
  const panel = page.getByRole("dialog");
  const after = await marker.boundingBox();
  expect(after?.y).toBe(before?.y);
  const box = await panel.boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  await expect(panel.getByRole("combobox").first()).toContainText(language === "ru" ? "ноябрь" : language === "kk" ? "қараша" : "November");
  await panel.getByRole("combobox").first().click();
  await expect(panel.getByRole("option")).toHaveCount(12);
  await page.keyboard.press("Escape");
  await expect(panel).toBeVisible();
  await page.screenshot({ path: `../output/calendar-shared-20261103/${language}-mobile.png` });
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(page.getByTestId("calendar-period-picker")).not.toContainText("M11");
});
