import { expect, test } from "@playwright/test";

test("embedded widget shares semantic colors through loading and failure without sending externally", async ({ page }, testInfo) => {
  let finishRequest!: () => void;
  const pending = new Promise<void>((resolve) => { finishRequest = resolve; });
  await page.route("**/api/public/website-chat/color-audit/**", async (route) => {
    await pending;
    await route.fulfill({ status: 503, json: { detail: "Color audit fixture failure" } });
  });
  await page.goto("/e2e/fixtures/widget-colors.html");
  const bubble = page.getByRole("button", { name: "Open PlatformaCRM chat" });
  await expect(bubble).toHaveCSS("background-color", "rgb(0, 122, 89)");
  await bubble.hover();
  await expect(bubble).toHaveCSS("background-color", "rgb(0, 102, 75)");
  await bubble.click();
  const field = page.getByPlaceholder("Сообщение...");
  await expect(field).toBeFocused();
  await expect(field).toHaveCSS("outline-color", "rgb(0, 122, 89)");
  await field.fill("Color audit fixture");
  const send = page.getByRole("button", { name: "Send", exact: true });
  await send.click();
  await expect(send).toBeDisabled();
  await expect(send).toHaveCSS("background-color", "rgb(238, 241, 239)");
  await expect(send).toHaveCSS("color", "rgb(114, 128, 120)");
  finishRequest();
  await expect(send).toBeEnabled();
  await expect(page.getByText("Не удалось отправить сообщение. Попробуйте позже.")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("widget.png"), fullPage: true });
});
