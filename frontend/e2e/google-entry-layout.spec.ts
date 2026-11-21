import { test, expect } from "@playwright/test";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

const dictionaries = { ru, kk, en };
for (const entry of ["login", "signup"]) {
  test(`${entry}: a late Google expansion stays hidden until it fits again`, async ({ page }) => {
    await page.clock.install();
    await page.route(url => url.pathname.startsWith("/api/"), route => route.fulfill({
      status: /csrf|google\/start/.test(route.request().url()) ? 200 : 401,
      json: route.request().url().includes("csrf") ? { csrf_token: "synthetic" } : { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 },
    }));
    await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({
      contentType: "application/javascript", body: `window.google={accounts:{id:{initialize(){},renderButton(parent,options){
        const wrapper=document.createElement('div');wrapper.style.height='40px';
        const button=document.createElement('button');button.textContent='Google';button.style.cssText='height:40px;width:'+options.width+'px';
        wrapper.append(button);parent.append(wrapper);
        setTimeout(()=>{wrapper.style.height='80px';},1000);
        setTimeout(()=>{wrapper.style.height='40px';},2000);
      }}}};`,
    }));
    await page.goto(`/${entry}`);
    const button = page.getByRole("button", { name: "Google", exact: true });
    await expect(button).toBeVisible();
    const before = await button.boundingBox();
    await page.clock.runFor(1100);
    await expect(button).toBeHidden();
    await expect(page.getByRole("status")).toBeVisible();
    await page.clock.runFor(1000);
    await expect(button).toBeVisible();
    await expect(page.getByRole("status")).toHaveCount(0);
    expect((await button.boundingBox())!.y).toBe(before!.y);
  });
}
for (const entry of ["login", "signup"]) {
  test(`${entry}: a Google role-button is ready beside a zero-size iframe`, async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await page.route(url => url.pathname.startsWith("/api/"), route => route.fulfill({
      status: /csrf|google\/start/.test(route.request().url()) ? 200 : 401,
      json: route.request().url().includes("csrf") ? { csrf_token: "synthetic" } : { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 },
    }));
    await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({
      contentType: "application/javascript", body: `window.google={accounts:{id:{initialize(){},renderButton(parent,options){
        const wrapper=document.createElement('div');wrapper.style.height='40px';
        const iframe=document.createElement('iframe');iframe.style.cssText='width:0;height:0;border:0;display:block';
        const button=document.createElement('div');button.role='button';button.tabIndex=0;button.textContent='Google';
        button.style.cssText='height:40px;width:'+options.width+'px';
        wrapper.append(iframe,button);parent.append(wrapper);
      }}}};`,
    }));
    for (const reload of [false, true]) {
      if (reload) await page.reload(); else await page.goto(`/${entry}`);
      const button = page.getByRole("button", { name: "Google", exact: true });
      await expect(button).toBeVisible();
      await expect(page.getByRole("status")).toHaveCount(0);
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(button.locator("xpath=ancestor::div[@aria-busy]")).toHaveAttribute("aria-busy", "false");
      await button.focus();
      await expect(button).toBeFocused();
      const size = page.viewportSize()!;
      await page.setViewportSize({ width: size.width - 30, height: size.height });
      await expect(page.getByRole("button", { name: "Google", exact: true })).toBeFocused();
    }
  });
}
for (const entry of ["login", "signup"]) {
  test(`${entry}: unfinished Google rendering times out and retries without losing input`, async ({ page }) => {
    await page.clock.install();
    await page.addInitScript(() => localStorage.setItem("ai_smb_language", "ru"));
    await page.route(url => url.pathname.startsWith("/api/"), route => route.fulfill({
      status: /csrf|google\/start/.test(route.request().url()) ? 200 : 401,
      json: route.request().url().includes("csrf") ? { csrf_token: "synthetic" } : { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 },
    }));
    await page.route("https://accounts.google.com/gsi/client", route => route.fulfill({
      contentType: "application/javascript", body: `let renders=0;
      window.google={accounts:{id:{initialize(){},renderButton(parent){
        const boot=document.createElement('div');boot.style.height=++renders===1?'80px':'40px';
        const b=document.createElement('button');b.textContent='Google';b.style.height='40px';
        boot.appendChild(b);parent.appendChild(boot);
      }}}};`,
    }));
    await page.goto(`/${entry}`);
    await page.locator('input[name="email"]').fill("retained@example.test");
    await expect(page.locator('button').filter({ hasText: /^Google$/ })).toBeHidden();
    await expect(page.getByRole("status")).toBeVisible();
    await page.clock.fastForward(15_001);
    await expect(page.getByRole("alert")).toHaveText(ru["auth.socialFailed"]);
    const retry = page.getByRole("button", { name: ru["common.retry"] });
    await retry.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Google", exact: true })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("status")).toHaveCount(0);
    await expect(page.locator('input[name="email"]')).toHaveValue("retained@example.test");
  });
}
for (const entry of ["login", "signup"]) for (const language of ["ru", "kk", "en"] as const) {
  test(`${entry} ${language}: loading Google does not move the form`, async ({ page }, info) => {
    await page.addInitScript(lang => localStorage.setItem("ai_smb_language", lang), language);
    await page.route(url => url.pathname.startsWith("/api/"), route => route.fulfill({
      status: /csrf|google\/start/.test(route.request().url()) ? 200 : 401,
      json: route.request().url().includes("csrf") ? { csrf_token: "synthetic" } : { nonce: "synthetic", flow_id: "s".repeat(43), expires_in: 600 },
    }));
    let release!: () => void;
    const waiting = new Promise<void>(resolve => { release = resolve; });
    await page.route("https://accounts.google.com/gsi/client", async route => {
      await waiting;
      await route.fulfill({ contentType: "application/javascript", body: `window.google={accounts:{id:{initialize(){},renderButton(parent,options){
        const boot=document.createElement('div');boot.style.height='80px';
        const b=document.createElement('button');b.textContent='Google';
        b.dataset.size=options.size;
        b.style.cssText='display:block;height:40px;padding:0;border:1px solid #dadce0';
        b.style.width=options.width+'px';boot.appendChild(b);parent.appendChild(boot);
        const inspect=()=>{if(!b.dataset.ready){
          if(getComputedStyle(b).visibility!=='hidden')b.dataset.bootExposed='true';
          requestAnimationFrame(inspect);
        }};requestAnimationFrame(inspect);
        setTimeout(()=>{boot.style.height='40px';b.dataset.ready='true';},250);
      }}}};` });
    });
    await page.goto(`/${entry}`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("status")).toHaveText(dictionaries[language]["googleAuth.loading"]);
    await page.evaluate(() => document.fonts.ready);
    const card = page.locator(".serenity-login__card");
    const before = await card.boundingBox();
    const inputBefore = await page.locator('input[name="email"]').boundingBox();
    await card.evaluate(element => {
      const samples: number[] = [];
      const observer = new ResizeObserver(() => samples.push(element.getBoundingClientRect().height));
      observer.observe(element);
      Object.assign(element, { googleBootSamples: samples, googleBootObserver: observer });
    });
    release();
    await expect(page.getByRole("button", { name: "Google", exact: true })).toHaveAttribute("data-ready", "true");
    await expect(page.getByRole("button", { name: "Google", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Google", exact: true })).toHaveAttribute("data-size", "large");
    await expect(page.getByRole("button", { name: "Google", exact: true })).not.toHaveAttribute("data-boot-exposed", "true");
    await expect(page.getByRole("status")).toHaveCount(0);
    const bootstrapHeights = await card.evaluate(element => {
      const observed = element as HTMLElement & { googleBootSamples: number[]; googleBootObserver: ResizeObserver };
      observed.googleBootObserver.disconnect();
      return observed.googleBootSamples;
    });
    expect(bootstrapHeights.length).toBeGreaterThan(0);
    expect(Math.max(...bootstrapHeights) - Math.min(...bootstrapHeights)).toBeLessThanOrEqual(1);
    const after = await card.boundingBox();
    const inputAfter = await page.locator('input[name="email"]').boundingBox();
    expect(Math.abs(after!.y - before!.y)).toBeLessThanOrEqual(1);
    expect(Math.abs(after!.height - before!.height)).toBeLessThanOrEqual(1);
    expect(Math.abs(inputAfter!.y - inputBefore!.y)).toBeLessThanOrEqual(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${entry}-${language}-stable.png`), fullPage: true });
  });
}
