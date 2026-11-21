import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.skip(process.env.GOOGLE_ENTRY_LIVE !== "1", "Requires an explicitly selected live Google environment");

for (const entry of ["login", "signup"]) {
  test(`${entry}: real Google first load and reload keep geometry`, async ({ page }, info) => {
    if (process.env.GOOGLE_ENTRY_ARTIFACT) {
      const root = path.resolve(process.env.GOOGLE_ENTRY_ARTIFACT);
      const origin = new URL(info.project.use.baseURL!).origin;
      await page.route(url => url.origin === origin && !url.pathname.startsWith("/api/"), async route => {
        const requested = path.resolve(root, "." + new URL(route.request().url()).pathname);
        const file = requested.startsWith(root + path.sep) && fs.existsSync(requested) && fs.statSync(requested).isFile()
          ? requested : path.join(root, "index.html");
        await route.fulfill({ path: file });
      });
    }
    await page.route(url => /\/api\/auth\/(google\/(verify|signup|link)|signup\/owner|token)\/$/.test(url.pathname), route => route.abort());
    await page.addInitScript(() => {
      const samples: { y: number; height: number; buttonY?: number; contentHeight?: number }[] = [];
      Object.assign(window, { googleGeometry: samples });
      function sample() {
        const card = document.querySelector(".serenity-login__card");
        const mount = card?.querySelector("[aria-busy] > div > div");
        if (card && mount) {
          const rect = card.getBoundingClientRect();
          const control = Array.from(mount.querySelectorAll<HTMLElement>('iframe, button, [role="button"]'))
            .find(element => element.clientHeight > 0 && element.clientWidth > 0);
          const visible = getComputedStyle(mount).visibility === "visible" && control;
          samples.push({ y: rect.y, height: rect.height,
            // GIS iframe borders and its HTML button have different insets; track their shared visible wrapper.
            buttonY: visible ? mount.firstElementChild?.getBoundingClientRect().y : undefined,
            contentHeight: visible ? mount.firstElementChild?.getBoundingClientRect().height : undefined });
        }
        if (samples.length < 3600) requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
    });
    for (const phase of ["first", "reload"]) {
      if (phase === "first") await page.goto(`/${entry}`); else await page.reload();
      await expect(page.locator(".serenity-login__card [aria-busy]")).toHaveAttribute("aria-busy", "false", { timeout: 20_000 });
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(page.locator('iframe[src*="accounts.google.com/gsi/button"]')).toHaveAttribute("src", /[?&]size=medium(?:&|$)/);
      const inlineButton = page.getByRole("button", { name: /Google/ });
      const framedButton = page.frameLocator('iframe[src*="accounts.google.com/gsi/button"]').getByRole("button");
      await expect.poll(async () => await inlineButton.isVisible() || await framedButton.isVisible()).toBe(true);
      if (await framedButton.isVisible()) {
        await framedButton.evaluate(async () => { await document.fonts.ready; });
      }
      await page.evaluate(async () => {
        await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      });
      const samples = await page.evaluate(() => (window as unknown as { googleGeometry: { y: number; height: number; buttonY?: number; contentHeight?: number }[] }).googleGeometry);
      const visible = samples.filter(value => value.buttonY !== undefined);
      expect(samples.length).toBeGreaterThan(2);
      expect(visible.length).toBeGreaterThan(0);
      const spread = (values: number[]) => Math.max(...values) - Math.min(...values);
      const result = { cardY: spread(samples.map(value => value.y)), cardHeight: spread(samples.map(value => value.height)), buttonY: spread(visible.map(value => value.buttonY!)), maxContentHeight: Math.max(...visible.map(value => value.contentHeight!)) };
      console.log(info.project.name, entry, phase, JSON.stringify(result));
      expect(result.cardY).toBeLessThanOrEqual(1);
      expect(result.cardHeight).toBeLessThanOrEqual(1);
      expect(result.buttonY).toBeLessThanOrEqual(1);
      expect(result.maxContentHeight).toBeLessThanOrEqual(44);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await expect(page.locator(".serenity-login__card [aria-busy]")).toHaveAttribute("aria-busy", "false");
      await expect(page.getByRole("status")).toHaveCount(0);
      await page.screenshot({ path: info.outputPath(`${entry}-${phase}.png`), fullPage: true });
    }
  });
}
