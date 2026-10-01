import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";

test("signup links open empty public documents without losing the form", async ({ page, context }) => {
  await page.goto("/signup");
  await page.locator('input[name="full_name"]').fill("Document draft");
  const documents = page.getByTestId("signup-documents");
  await expect(documents.getByRole("checkbox")).toHaveCount(4);
  const submit = page.locator('form button[type="submit"]');
  await expect(submit).toBeDisabled();
  for (const link of await documents.getByRole("link").all()) {
    const title = await link.innerText();
    const opened = context.waitForEvent("page");
    await link.click();
    const document = await opened;
    await expect(document.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(document.locator("[data-document-body]")).toBeEmpty();
    await document.close();
  }
  await expect(page.locator('input[name="full_name"]')).toHaveValue("Document draft");
  const boxes = documents.getByRole("checkbox");
  for (let index = 0; index < 3; index++) await boxes.nth(index).check();
  await expect(submit).toBeDisabled();
  await boxes.nth(3).check();
  await expect(submit).toBeEnabled();
  await boxes.nth(0).uncheck();
  await expect(submit).toBeDisabled();
  await submit.scrollIntoViewIfNeeded();
  await expect(submit).toBeInViewport();
  await page.screenshot({ path: test.info().outputPath("signup-documents.png"), fullPage: true });
});

test("public Documents index and account footer expose all document links", async ({ page }) => {
  await page.goto("/documents");
  await expect(page.getByRole("heading", { name: "Документы", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Документы" }).getByRole("link")).toHaveCount(4);
  await crmSession(page);
  await page.goto("/app/account");
  const footer = page.getByTestId("account-documents");
  await footer.scrollIntoViewIfNeeded();
  await expect(footer).toBeVisible();
  await expect(footer.getByRole("link")).toHaveCount(5);
  for (const link of await footer.getByRole("link").all()) {
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("href", /^\/documents/);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await page.screenshot({ path: test.info().outputPath("account-documents.png"), fullPage: true });
});
