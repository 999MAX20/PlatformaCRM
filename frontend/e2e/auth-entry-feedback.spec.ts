import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const dictionaries = { ru, kk, en };
const invitation = {
  business: 1, business_name: "Example workspace", email: "invite@example.test",
  full_name: "Example User", role: "admin", status: "pending",
  expires_at: "2099-01-01T00:00:00Z", requires_authentication: false,
  access_summary: [{ resource: "clients", action: "view", scope: "business" }],
};

test.beforeEach(async ({ page }, info) => {
  if (process.env.AUTH_ENTRY_ARTIFACT) {
    const root = path.resolve(process.env.AUTH_ENTRY_ARTIFACT);
    const origin = new URL(info.project.use.baseURL!).origin;
    await page.route(url => url.origin === origin && !url.pathname.startsWith("/api/"), async route => {
      const requested = path.resolve(root, "." + new URL(route.request().url()).pathname);
      const file = requested.startsWith(root + path.sep) && fs.existsSync(requested) && fs.statSync(requested).isFile()
        ? requested : path.join(root, "index.html");
      await route.fulfill({ path: file });
    });
  }
  // Every API request is intercepted: these tests never create or accept accounts.
  await page.route(url => url.pathname.startsWith("/api/"), route => {
    const url = route.request().url();
    if (url.includes("invitations/preview")) return route.fulfill({ json: invitation });
    if (url.includes("csrf")) return route.fulfill({ json: { csrf_token: "synthetic" } });
    if (url.includes("google/start")) return route.fulfill({ json: { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 } });
    return route.fulfill({ status: 401, json: { detail: "Synthetic unauthorized response" } });
  });
  await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({
    contentType: "application/javascript", body: `window.google={accounts:{id:{initialize(){},renderButton(parent,options){
      const b=document.createElement('button');b.textContent='Google';b.type='button';b.dataset.size=options.size;
      b.style.cssText='height:32px;width:'+options.width+'px';parent.append(b);
    }}}};`,
  }));
});

async function warns(page: Page) {
  return page.evaluate(() => {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  });
}

for (const language of ["ru", "kk", "en"] as const) {
  test(`signup ${language}: precise password feedback and retained fields`, async ({ page }, info) => {
    const t = dictionaries[language];
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/signup");
    await page.locator('[name="full_name"]').fill("Example User");
    await page.locator('[name="email"]').fill("example@example.test");
    await page.locator('[name="business_name"]').fill("Example workspace");
    let submissions = 0;
    page.on("request", request => { if (request.url().includes("signup/owner")) submissions++; });
    for (const [password, key] of [
      ["abc1", "signup.passwordMinCheck"],
      ["abcdefgh", "signup.passwordLettersNumbersCheck"],
      ["12345678", "signup.passwordLettersNumbersCheck"],
      ["abcd 1234", "signup.passwordNoSpacesCheck"],
    ] as const) {
      await page.locator('[name="password"]').fill(password);
      await page.locator('[name="password_confirm"]').fill(password);
      await page.locator('button[type="submit"]').click();
      await expect(page.getByRole("alert")).toContainText(t[key]);
    }
    expect(submissions).toBe(0);
    await expect(page.locator('[name="email"]')).toHaveValue("example@example.test");
    await page.locator('[name="password"]').fill("abcdefgh");
    await page.locator('[name="password_confirm"]').fill("abcdefgh");
    await page.locator('button[type="submit"]').click();
    await expect(page.getByRole("alert")).toContainText(t["signup.passwordLettersNumbersCheck"]);
    const errorFits = await page.getByRole("alert").evaluate(el => {
      const error = el.getBoundingClientRect();
      const field = el.closest("label")!.querySelector("input")!.getBoundingClientRect();
      return error.right <= field.right + 1 && el.scrollWidth <= el.clientWidth;
    });
    expect(errorFits).toBe(true);
    if (await page.locator(".serenity-login__social-row").count()) {
      await expect(page.getByRole("button", { name: "Google", exact: true })).toHaveAttribute("data-size", "medium");
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: info.outputPath(`signup-${language}.png`), fullPage: true });
  });

  test(`invitation ${language}: login background, role label, accessible form`, async ({ page }, info) => {
    const t = dictionaries[language];
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.goto("/login");
    const background = await page.locator("main").evaluate(el => getComputedStyle(el).backgroundImage);
    await page.goto("/invite/synthetic-preview");
    await expect(page.locator('[name="full_name"]')).toHaveValue(invitation.full_name);
    expect(await page.locator("main").evaluate(el => getComputedStyle(el).backgroundImage)).toBe(background);
    await expect(page.getByText(t["invite.assignedRole"], { exact: true })).toBeVisible();
    await expect(page.locator("details")).toHaveCount(0);
    await expect(page.getByText(t["settings.redesign.rolePreview"], { exact: true })).toHaveCount(0);
    await expect(page.locator(".serenity-login__ambient span")).toHaveCount(5);
    await page.locator('[name="full_name"]').focus();
    await page.keyboard.press("Tab");
    await expect(page.locator('[name="phone"]')).toBeFocused();
    await page.locator('button[type="submit"]').scrollIntoViewIfNeeded();
    await expect(page.locator('button[type="submit"]')).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: info.outputPath(`invite-${language}.png`), fullPage: true });
  });
}

for (const entry of ["signup", "invite/synthetic-preview"]) {
  test(`${entry}: reload warns only after edits; cancel retains and confirm clears`, async ({ page }) => {
    await page.goto(`/${entry}`);
    const field = page.locator(entry === "signup" ? '[name="full_name"]' : '[name="phone"]');
    await expect(field).toBeVisible();
    expect(await warns(page)).toBe(false);
    await field.fill("123456789");
    await expect.poll(() => warns(page)).toBe(true);
    await field.fill("");
    await expect.poll(() => warns(page)).toBe(false);
    await field.fill("123456789");
    await field.click();
    const dialogPromise = page.waitForEvent("dialog");
    await page.evaluate(() => { setTimeout(() => location.reload(), 0); });
    const dialog = await dialogPromise;
    expect(dialog.type()).toBe("beforeunload");
    await dialog.dismiss();
    await expect(field).toHaveValue("123456789");
    page.once("dialog", dialog => dialog.accept());
    await page.reload();
    await expect(field).toHaveValue("");
    expect(await warns(page)).toBe(false);
  });
}

test("signup: SPA navigation removes the unload warning", async ({ page }) => {
  await page.goto("/signup");
  await page.locator('[name="full_name"]').fill("Example User");
  await expect.poll(() => warns(page)).toBe(true);
  await page.locator('a.serenity-login__brand').click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await warns(page)).toBe(false);
});

test("invitation: preview retry and submission error retain input", async ({ page }) => {
  let attempts = 0;
  await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.route("**/api/team/invitations/preview/**", route => ++attempts === 1
    ? route.fulfill({ status: 503, json: { detail: "Unavailable" } })
    : route.fulfill({ json: invitation }));
  await page.route("**/api/team/invitations/accept/", route => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.goto("/invite/synthetic-preview");
  await expect(page.locator("main")).toHaveClass(/serenity-login--invitation/);
  await page.getByRole("button", { name: ru["common.retry"] }).click();
  await expect(page.locator('[name="full_name"]')).toHaveValue(invitation.full_name);
  await page.locator('[name="password"]').fill("Synthetic12345");
  await page.locator('[name="password_confirm"]').fill("Synthetic12345");
  await page.locator('button[type="submit"]').click();
  await expect(page.getByRole("alert")).toContainText(ru["fallback.title.temporary"]);
  await expect(page.locator('[name="password"]')).toHaveValue("Synthetic12345");
  await expect(page.locator('button[type="submit"]')).toBeEnabled();
  expect(await warns(page)).toBe(true);
});
