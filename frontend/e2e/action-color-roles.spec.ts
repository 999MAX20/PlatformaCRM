import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("semantic action color matrix", () => {
  test("roles remain distinct, focusable and responsive", async ({ page }) => {
    await page.goto("/e2e/fixtures/action-color-roles.html");

    const matrix = page.getByTestId("action-color-matrix");
    await expect(matrix).toBeVisible();
    await expect(matrix.locator("button")).toHaveCount(10);

    const backgrounds = await Promise.all(
      ["brand", "neutral", "warning", "danger", "ai"].map(async (tone) =>
        page.getByTestId(`tone-${tone}`).evaluate((element) => getComputedStyle(element).backgroundColor),
      ),
    );
    expect(new Set(backgrounds).size).toBe(5);

    const warning = page.getByTestId("tone-warning");
    await expect(warning).toHaveCSS("background-color", "rgb(255, 245, 232)");
    await warning.hover();
    await expect(warning).not.toHaveCSS("background-color", "rgb(255, 245, 232)");
    await warning.focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(warning).toHaveCSS("box-shadow", /rgb\(0, 122, 89\)/);
    await expect(page.getByTestId("tone-warning-disabled")).toHaveCSS("opacity", "1");
    await expect(page.getByTestId("tone-warning-disabled")).toHaveCSS("background-color", "rgb(238, 241, 239)");

    const overflow = await page.locator("body").evaluate((body) => body.scrollWidth - body.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);

    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });
});
