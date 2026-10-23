import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

const palette = JSON.parse(readFileSync(new URL("../src/theme/semantic-tokens.json", import.meta.url), "utf8"));

const rgb = (hex: string) => `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(", ")})`;

test.describe("semantic action color matrix", () => {
  test("roles remain distinct, focusable and responsive", async ({ page, isMobile }) => {
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
    await expect(warning).toHaveCSS("background-color", rgb(palette.tokens["warning.soft"]));
    if (!isMobile) {
      await warning.hover();
      await expect(warning).not.toHaveCSS("background-color", rgb(palette.tokens["warning.soft"]));
    }
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
