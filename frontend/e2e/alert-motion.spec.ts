import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function open(page: Page, language = "ru") {
  await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
  await page.route("**/ready/", route => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/inbox/conversations/summary/", route => route.fulfill({ json: { unread_messages: 0 } }));
  await page.goto("/e2e/fixtures/alert-components.html");
  await expect(page.getByTestId("draft")).toBeVisible();
}

for (const width of [320, 390, 768, 1440]) {
  test(`entry and timed exit never move vertically or create scrollbars ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 844 });
    await open(page);
    await page.evaluate(() => {
      const frames: { x: number; y: number; exit: boolean; overflow: boolean }[] = [];
      (window as unknown as { noticeFrames: typeof frames }).noticeFrames = frames;
      const start = performance.now();
      function sample() {
        const card = document.querySelector<HTMLElement>('.platforma-notification-slot:not([data-queued]) .platforma-notification-card');
        if (card) {
          const rect = card.getBoundingClientRect();
          const viewport = document.querySelector<HTMLElement>('.platforma-notification-viewport')!;
          frames.push({ x: rect.x, y: rect.y, exit: card.hasAttribute('data-leaving'), overflow: document.documentElement.scrollWidth > innerWidth || viewport.clientHeight !== viewport.offsetHeight });
        }
        if (performance.now() - start < 1800) requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
    });
    await page.getByTestId("short").click();
    await expect(page.getByTestId("action-feedback")).toBeVisible();
    await expect(page.getByTestId("action-feedback")).toHaveCount(0);
    const frames = await page.evaluate(() => (window as unknown as { noticeFrames: { x: number; y: number; exit: boolean; overflow: boolean }[] }).noticeFrames);
    const exit = frames.filter(frame => frame.exit);
    expect(exit.length).toBeGreaterThan(3);
    expect(Math.max(...frames.map(frame => frame.y)) - Math.min(...frames.map(frame => frame.y))).toBeLessThan(1);
    expect(frames.some(frame => frame.overflow)).toBe(false);
    expect(exit.at(-1)!.x).toBeGreaterThan(width - 20);
    await info.attach("animation-frames", { body: JSON.stringify(frames), contentType: "application/json" });
  });
}

for (const language of ["ru", "kk", "en"]) {
  test(`mobile admission preserves unread cards and full details ${language}`, async ({ page }, info) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await open(page, language);
    await page.getByTestId("queue").click();
    const visible = page.locator('.platforma-notification-slot:not([data-queued])').getByTestId('action-feedback');
    await expect(visible).toHaveCount(1);
    await expect(visible).toContainText('Queue 0');
    await page.getByTestId('queued-short').click();
    await page.waitForTimeout(1300);
    for (let i = 0; i < 5; i++) {
      await expect(visible).toContainText(`Queue ${i}`);
      await visible.getByRole('button').click();
    }
    await expect(visible).toContainText('Pending short');
    await expect(visible).toHaveCount(0);
    await page.getByTestId('long').click();
    const details = page.locator('.platforma-notification-details');
    await expect(details).toBeVisible();
    await details.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByTestId('notification-details');
    await expect(dialog).toBeVisible();
    await expect(dialog.locator('.platforma-notice-description')).toContainText(language === 'ru' ? 'Если проблема' : language === 'en' ? 'If' : /.+/);
    await page.screenshot({ path: info.outputPath(`details-${language}.png`) });
    expect((await new AxeBuilder({ page }).include('[data-testid="notification-details"]').withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(details).toBeFocused();
    await page.screenshot({ path: info.outputPath(`preview-${language}.png`) });
  });
}

test('short viewport queues tall cards and keeps all admitted controls inside viewport', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 400 });
  await open(page);
  await page.getByTestId('stack').click();
  await page.waitForTimeout(300);
  const visible = page.locator('.platforma-notification-slot:not([data-queued])');
  expect(await visible.count()).toBeLessThan(5);
  const boxes = await visible.evaluateAll(nodes => nodes.map(node => {const r=node.getBoundingClientRect();return {top:r.top,bottom:r.bottom};}));
  for (const box of boxes) { expect(box.top).toBeGreaterThanOrEqual(24);expect(box.bottom).toBeLessThanOrEqual(376); }
});
