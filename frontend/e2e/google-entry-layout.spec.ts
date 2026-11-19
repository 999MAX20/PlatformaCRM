import { test, expect } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const dictionaries = { ru, kk, en };
for (const entry of ["login", "signup"]) for (const language of ["ru", "kk", "en"] as const) {
  test(`${entry} ${language}: loading Google does not move the form`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.route("**/api/**", route => route.fulfill({
      status: /csrf|google\/start/.test(route.request().url()) ? 200 : 401,
      json: route.request().url().includes("csrf") ? { csrf_token: "synthetic" } : { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 },
    }));
    let release!: () => void;
    const waiting = new Promise<void>(resolve => { release = resolve; });
    await page.route("https://accounts.google.com/gsi/client", async route => {
      await waiting;
      await route.fulfill({ contentType: "application/javascript", body: `window.google={accounts:{id:{initialize(){},renderButton(parent,options){const b=document.createElement('button');b.textContent='Google';b.style.cssText='display:block;height:32px;padding:0;border:1px solid #dadce0';b.style.width=options.width+'px';parent.appendChild(b)}}}};` });
    });
    await page.goto(`/${entry}`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("status")).toHaveText(dictionaries[language]["googleAuth.loading"]);
    await page.evaluate(() => document.fonts.ready);
    const card = page.locator(".serenity-login__card");
    const before = await card.boundingBox();
    const inputBefore = await page.locator('input[name="email"]').boundingBox();
    release();
    await expect(page.getByRole("button", { name: "Google", exact: true })).toBeVisible();
    await expect(page.getByRole("status")).toHaveCount(0);
    const after = await card.boundingBox();
    const inputAfter = await page.locator('input[name="email"]').boundingBox();
    expect(Math.abs(after!.y - before!.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(after!.height - before!.height)).toBeLessThanOrEqual(1);
    expect(Math.abs(inputAfter!.y - inputBefore!.y)).toBeLessThanOrEqual(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${entry}-${language}-stable.png`), fullPage: true });
  });
}
