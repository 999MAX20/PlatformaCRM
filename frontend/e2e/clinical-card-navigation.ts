import { expect, type Page } from "@playwright/test";

const entries = new WeakMap<Page, URL>();

export async function openClinicalWorkspace(page: Page, reopen = false) {
  const workspace = page.getByTestId("clinical-workspace");
  await page.getByTestId("calendar-workspace-ready").waitFor();
  if (!reopen) entries.set(page, new URL(page.url()));
  if (reopen) {
    const url = entries.get(page)!;
    await page.locator(`[data-calendar-day="${url.searchParams.get("date")}"]`).click();
    await page.locator(`[data-appointment-id="${url.searchParams.get("appointment")}"]`).click();
  }
  await expect(workspace).toBeVisible();
}
