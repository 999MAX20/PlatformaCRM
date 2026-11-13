import type { Page } from "@playwright/test";

export async function openAgentSection(page: Page, name: string) {
  const links = page.locator("#agent-section-links");
  await links.locator("..").waitFor({ state: "visible" });
  if (!await links.isVisible()) await links.locator("..").locator(":scope > button").click();
  await links.getByRole("button", { name, exact: true }).click();
}
