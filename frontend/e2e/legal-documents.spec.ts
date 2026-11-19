import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const dictionaries = { ru, kk, en };

for (const language of ["ru", "kk", "en"] as const) {
  test(`${language}: signup submit carries consent and preserves input on retry`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    const payloads: Record<string, unknown>[] = [];
    await page.route("**/api/auth/signup/owner/", route => {
      payloads.push(route.request().postDataJSON());
      return route.fulfill({ status: 503, json: { detail: "Synthetic signup failure" } });
    });
    await page.goto("/signup");
    const fields = { full_name: "Signup fixture", email: "invalid", business_name: "Synthetic business", password: "SyntheticConsent928!", password_confirm: "SyntheticConsent928!" };
    for (const [name, value] of Object.entries(fields)) await page.locator(`input[name="${name}"]`).fill(value);
    const submit = page.locator('form button[type="submit"]');
    await submit.click();
    await expect(page.locator('input[name="email"]')).toBeFocused();
    expect(payloads).toHaveLength(0);
    await page.locator('input[name="email"]').fill("consent@example.invalid");
    await submit.click();
    await expect(page.getByRole("alert")).toHaveText(dictionaries[language]["actions.errorTemporary"]);
    expect(payloads).toHaveLength(1);
    expect(payloads[0].acceptance_method).toBe("signup_submit");
    expect(payloads[0].accepted_documents).toEqual(["terms", "privacy", "personal-data", "company-data"]);
    expect(payloads[0]).not.toHaveProperty("phone");
    expect(payloads[0].business_type).toBe("other");
    await expect(page.locator('input[name="full_name"]')).toHaveValue(fields.full_name);
    await submit.click();
    await expect.poll(() => payloads.length).toBe(2);
    const notice = page.getByTestId("signup-documents");
    await expect(notice.locator('input[type="checkbox"]')).toHaveCount(0);
    await expect(submit).toHaveAttribute("aria-describedby", "signup-consent-notice");
    await notice.getByRole("link").focus();
    await expect(notice.getByRole("link")).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight)).toBe(true);
    await page.screenshot({ path: info.outputPath(`signup-consent-${language}.png`), fullPage: true });
  });
}

test("signup notice opens all public documents without losing the form", async ({ page, context }) => {
  await page.goto("/signup");
  await page.locator('input[name="full_name"]').fill("Document draft");
  const documents = page.getByTestId("signup-documents");
  await expect(documents.getByRole("checkbox")).toHaveCount(0);
  const submit = page.locator('form button[type="submit"]');
  await expect(submit).toBeEnabled();
  const openedIndex = context.waitForEvent("page");
  await documents.getByRole("link").click();
  const index = await openedIndex;
  await expect(index).toHaveURL(/\/documents$/);
  const links = index.getByRole("navigation").getByRole("link");
  await expect(links).toHaveCount(4);
  const paths = await links.evaluateAll(items => items.map(item => ({ href: item.getAttribute("href")!, title: item.textContent! })));
  for (const {href, title} of paths) {
    await index.goto(href);
    await expect(index.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(index.locator("[data-document-body]")).toBeEmpty();
  }
  await index.close();
  await expect(page.locator('input[name="full_name"]')).toHaveValue("Document draft");
  await submit.scrollIntoViewIfNeeded();
  await expect(submit).toBeInViewport();
  await page.screenshot({ path: test.info().outputPath("signup-documents.png"), fullPage: true });
});

test("public Documents index and account footer expose all document links", async ({ page }) => {
  await page.goto("/documents");
  await expect(page.getByRole("heading", { name: "Документы", exact: true })).toBeVisible();
  const content = await page.locator("[data-documents-content]").boundingBox();
  const viewport = page.viewportSize()!;
  expect(Math.abs(content!.x + content!.width / 2 - viewport.width / 2)).toBeLessThan(2);
  expect(Math.abs(content!.y + content!.height / 2 - viewport.height / 2)).toBeLessThan(2);
  await page.screenshot({ path: test.info().outputPath("documents-index.png") });
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

test("signup fits desktop viewports without page scrolling", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "Desktop fit matrix; mobile reachability is covered by the document-link flow.");
  for (const [width, height] of [[1280, 720], [1366, 618], [1536, 696], [1920, 870]]) {
    await page.setViewportSize({ width, height });
    await page.goto("/signup");
    const card = page.locator(".serenity-login__card--signup");
    await expect(card).toBeVisible();
    const bounds = await card.boundingBox();
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(await page.locator(".serenity-login__layout").evaluate(element => getComputedStyle(element).overflowY)).toBe("hidden");
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(height);
    await page.screenshot({ path: testInfo.outputPath(`signup-${width}x${height}.png`) });
  }
});
