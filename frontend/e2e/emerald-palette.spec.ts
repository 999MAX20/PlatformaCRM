import { expect, test, type Locator } from "@playwright/test";

async function textContrast(element: Locator) {
  return element.evaluate((node) => {
    const style = getComputedStyle(node);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const context = canvas.getContext("2d")!;
    const luminance = (color: string) => {
      context.fillStyle = "white";
      context.fillRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const rgb = [...context.getImageData(0, 0, 1, 1).data].slice(0, 3).map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
    };
    const foreground = luminance(style.color);
    const background = luminance(style.backgroundColor);
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
  });
}

test("semantic actions retain readable default, hover, pressed, focus and disabled states", async ({ page }, testInfo) => {
  await page.goto("/e2e/fixtures/action-color-roles.html");
  await expect(page.getByTestId("action-color-matrix")).toBeVisible();
  const colors = {
    brand: ["rgb(0, 122, 89)", "rgb(0, 102, 75)", "rgb(0, 84, 62)"],
    danger: ["rgb(163, 59, 53)", "rgb(143, 48, 43)", "rgb(118, 38, 32)"],
    ai: ["rgb(111, 76, 195)", "rgb(94, 60, 174)", "rgb(94, 60, 174)"],
    neutral: ["rgb(255, 255, 255)", "rgb(234, 240, 237)", "rgb(240, 244, 242)"],
  };
  for (const [tone, states] of Object.entries(colors)) {
    const button = page.getByTestId(`tone-${tone}`);
    await expect(button).toHaveCSS("background-color", states[0]);
    expect(await textContrast(button)).toBeGreaterThanOrEqual(4.5);
    await button.hover();
    await expect(button).toHaveCSS("background-color", states[1]);
    expect(await textContrast(button)).toBeGreaterThanOrEqual(4.5);
    await page.mouse.down();
    await expect(button).toHaveCSS("background-color", states[2]);
    expect(await textContrast(button)).toBeGreaterThanOrEqual(4.5);
    await page.mouse.up();
    await button.focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(button).toBeFocused();
    await expect(button).toHaveCSS("box-shadow", /rgb\(0, 122, 89\)/);
  }
  const warning = page.getByTestId("tone-warning");
  await expect(warning).toHaveCSS("background-color", "rgb(240, 244, 242)");
  expect(await textContrast(warning)).toBeGreaterThanOrEqual(4.5);
  await warning.hover();
  await expect(warning).not.toHaveCSS("background-color", "rgb(240, 244, 242)");
  await warning.evaluate((node) => Promise.all(node.getAnimations().map((animation) => animation.finished)));
  const hoverColor = await warning.evaluate((node) => getComputedStyle(node).backgroundColor);
  expect(await textContrast(warning)).toBeGreaterThanOrEqual(4.5);
  await page.mouse.down();
  await expect(warning).not.toHaveCSS("background-color", hoverColor);
  await warning.evaluate((node) => Promise.all(node.getAnimations().map((animation) => animation.finished)));
  expect(await textContrast(warning)).toBeGreaterThanOrEqual(4.5);
  await page.mouse.up();
  for (const tone of ["brand", "neutral", "warning", "danger", "ai"]) {
    const disabled = page.getByTestId(`tone-${tone}-disabled`);
    await expect(disabled).toBeDisabled();
    await expect(disabled).toHaveCSS("background-color", "rgb(238, 241, 239)");
    await expect(disabled).toHaveCSS("color", "rgb(114, 128, 120)");
    await expect(disabled).toHaveCSS("opacity", "1");
  }
  await expect(page.getByTestId("loading-button")).toBeDisabled();
  await expect(page.getByTestId("loading-button")).toHaveAttribute("aria-busy", "true");
  expect(await page.locator("body").evaluate((body) => body.scrollWidth - body.clientWidth)).toBeLessThanOrEqual(1);
  await page.screenshot({ path: testInfo.outputPath("semantic-actions.png"), fullPage: true });
});

test("fields, checkbox, switch and tabs share keyboard focus and selected colors", async ({ page }, testInfo) => {
  await page.goto("/e2e/fixtures/action-color-roles.html");
  const field = page.getByRole("textbox", { name: "Editable field", exact: true });
  await expect(field).toHaveCSS("border-color", "rgb(131, 152, 141)");
  await field.hover();
  await expect(field).toHaveCSS("border-color", "rgb(0, 122, 89)");
  await field.focus();
  await expect(field).toHaveCSS("outline-color", "rgb(0, 122, 89)");
  await expect(page.getByRole("textbox", { name: "Invalid field" })).toHaveCSS("border-color", "rgb(163, 59, 53)");
  await expect(page.getByRole("textbox", { name: "Read-only field" })).toHaveCSS("background-color", "rgb(240, 244, 242)");
  await expect(page.getByTestId("warning-alpha")).toHaveCSS("background-color", "rgba(240, 244, 242, 0.45)");
  await expect(page.getByTestId("danger-alpha")).toHaveCSS("background-color", "rgba(240, 244, 242, 0.6)");
  await expect(page.getByTestId("inbox-action-composer")).toBeDisabled();
  await expect(page.getByTestId("inbox-action-composer")).toHaveCSS("background-color", "rgb(238, 241, 239)");
  for (const name of ["Disabled field", "Disabled select"]) {
    const control = page.getByRole(name.includes("select") ? "combobox" : "textbox", { name: new RegExp(`^${name}`) });
    await expect(control).toBeDisabled();
    await expect(control).toHaveCSS("background-color", "rgb(238, 241, 239)");
  }
  const select = page.getByRole("combobox", { name: /Selected option/ });
  await select.focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(select).toContainText("Second");
  await select.click();
  await expect(page.getByRole("option", { name: "Second", exact: true })).toHaveCSS("background-color", "rgb(228, 243, 237)");
  await page.keyboard.press("Escape");
  const checkbox = page.getByRole("checkbox", { name: "Select record" });
  await checkbox.focus();
  await page.keyboard.press("Space");
  await expect(checkbox).toBeChecked();
  await expect(checkbox).toHaveCSS("accent-color", "rgb(0, 122, 89)");
  const radio = page.getByRole("radio", { name: "Select radio" });
  await radio.focus();
  await page.keyboard.press("Space");
  await expect(radio).toBeChecked();
  await expect(radio).toHaveCSS("accent-color", "rgb(0, 122, 89)");
  const toggle = page.getByRole("switch", { name: "Enabled preference" });
  await toggle.focus();
  await page.keyboard.press("Space");
  await expect(toggle).toBeChecked();
  await page.mouse.move(0, 0);
  await expect(toggle).toHaveCSS("background-color", "rgb(0, 122, 89)");
  await page.getByRole("tab", { name: "First view" }).focus();
  await page.keyboard.press("ArrowRight");
  const selected = page.getByRole("tab", { name: "Second view" });
  await expect(selected).toHaveAttribute("aria-selected", "true");
  await expect(selected).toHaveCSS("background-color", "rgb(228, 243, 237)");
  await expect(selected).toBeFocused();
  expect(await textContrast(selected)).toBeGreaterThanOrEqual(4.5);
  await page.getByRole("button", { name: "Tooltip trigger" }).hover();
  const tooltip = page.getByText("Tooltip content", { exact: true });
  await expect(tooltip).toHaveCSS("opacity", "1");
  await expect(tooltip).toHaveCSS("background-color", "rgb(23, 32, 30)");
  await expect(tooltip).toHaveCSS("color", "rgb(255, 255, 255)");
  await page.getByRole("button", { name: "Record actions" }).click();
  const disabledAction = page.getByRole("menuitem", { name: "Delete unavailable" });
  await expect(disabledAction).toBeDisabled();
  await expect(disabledAction).toHaveCSS("opacity", "1");
  await expect(disabledAction).toHaveCSS("background-color", "rgb(238, 241, 239)");
  await expect(disabledAction).toHaveCSS("color", "rgb(114, 128, 120)");
  await page.keyboard.press("Escape");
  await page.screenshot({ path: testInfo.outputPath("semantic-controls.png"), fullPage: true });
});
