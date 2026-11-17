import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const evidence = path.resolve(process.env.ALERT_EVIDENCE_DIR || "../output/alert-components-20261102");
async function open(page: Page, language = "ru") {
  await page.addInitScript(language => localStorage.setItem("ai_smb_language", language), language);
  await page.route("**/ready/", route => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/inbox/conversations/summary/", route => route.fulfill({ json: { unread_messages: 0 } }));
  await page.goto("/e2e/fixtures/alert-components.html");
  await expect(page.getByTestId("draft")).toBeVisible();
  await expect(page.getByTestId("connectivity-banner")).toHaveCount(0);
}

for (const language of ["ru", "kk", "en"]) {
  for (const width of [1440, 768, 390, 320]) {
    test(`stack, contrast and reflow ${language} ${width}`, async ({ page, context }) => {
      await page.setViewportSize({ width, height: 1000 });
      await open(page, language);
      await page.getByTestId("stack").click();
      await context.setOffline(true);
      const host = page.getByTestId("notification-host");
      await expect(host.getByTestId("action-feedback")).toHaveCount(5);
      await expect(host.getByTestId("connectivity-banner")).toBeVisible();
      await page.waitForTimeout(250);
      const result = await host.evaluate(element => {
        const rect = element.getBoundingClientRect();
        const cards = Array.from(element.querySelectorAll<HTMLElement>(".platforma-notification-slot:not([data-queued]) .platforma-status-notice")).map(node => {
          const style = getComputedStyle(node), box = node.getBoundingClientRect();
          const title = node.querySelector(".platforma-notice-title")!;
          const titleStyle = getComputedStyle(title);
          return { tone: node.dataset.noticeTone, background: style.backgroundColor, color: style.color, padding: style.padding, radius: style.borderRadius, width: box.width, top: box.top, bottom: box.bottom, font: titleStyle.fontSize, line: titleStyle.lineHeight, atomic: node.getAttribute("aria-atomic") };
        });
        return { cards, host: { left: rect.left, right: rect.right, bottom: rect.bottom, width: rect.width }, overflow: document.documentElement.scrollWidth > innerWidth, navTop: document.querySelector('[data-testid="bottom-mobile-menu-trigger"]')?.closest("nav")?.getBoundingClientRect().top };
      });
      expect(result.overflow).toBe(false);
      expect(result.host.width).toBeLessThanOrEqual(380);
      expect(width - result.host.right).toBe(width <= 760 ? 16 : 24);
      if (width < 1024) expect(result.navTop! - result.host.bottom).toBe(width <= 760 ? 16 : 24);
      const colors: Record<string, [string, string]> = { success: ["rgb(0, 122, 89)", "rgb(255, 255, 255)"], danger: ["rgb(163, 59, 53)", "rgb(255, 255, 255)"], warning: ["rgb(244, 197, 66)", "rgb(23, 32, 30)"], info: ["rgb(36, 94, 138)", "rgb(255, 255, 255)"] };
      for (const card of result.cards) {
        expect([card.background, card.color]).toEqual(colors[card.tone!]);
        expect([card.padding, card.radius, card.font, card.line, card.atomic]).toEqual(["16px", "12px", "14px", "21px", "true"]);
      }
      for (let i = 1; i < result.cards.length; i++) expect(result.cards[i].bottom).toBeLessThanOrEqual(result.cards[i - 1].top - 7);
      for (const card of result.cards) expect(card.top).toBeGreaterThanOrEqual(width <= 760 ? 16 : 24);
      if (width <= 760) expect(result.cards.length).toBeLessThanOrEqual(3);
      const lastVisible = host.locator('.platforma-notification-slot:not([data-queued])').getByTestId("action-feedback").last();
      await lastVisible.getByRole("button").first().focus();
      await expect(lastVisible.getByRole("button").first()).toBeFocused();
      await page.screenshot({ path: path.join(evidence, `stack-${language}-${width}.png`) });
      await fs.writeFile(path.join(evidence, `computed-${language}-${width}.json`), JSON.stringify(result, null, 2));
    });
  }
}

test("long text stays inside the card and controls remain reachable", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await open(page);
  await page.getByTestId("long").click();
  const card = page.getByTestId("notification-host").getByTestId("action-feedback");
  await expect(card).toBeVisible();
  expect(await card.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  await card.getByRole("button").click();
  await expect(card).toHaveCount(0);
  await expect(page.getByTestId("long")).toBeFocused();
});

test("queue retains visible notices and admits pending FIFO without losing focus", async ({ page }) => {
  await open(page);
  await page.getByTestId("queue").click();
  const host = page.getByTestId("notification-host");
  await expect(host.getByTestId("action-feedback")).toHaveCount(4);
  await expect(host).toContainText("Queue 0");
  await expect(host).not.toContainText("Queue 4");
  await expect(host.getByTestId("action-feedback").first()).toContainText("Queue 0");
  await page.getByTestId("remove-opener").click();
  const close = host.getByTestId("action-feedback").filter({ hasText: "Queue 3" }).getByRole("button");
  await close.focus();
  await page.keyboard.press("Enter");
  await expect(host.getByTestId("action-feedback")).toHaveCount(4);
  await expect(host.getByTestId("action-feedback").last()).toContainText("Queue 4");
  await expect(host).not.toContainText("Queue 3");
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY");
});

test("dismiss returns usable focus when the original opener was removed", async ({ page }) => {
  await open(page);
  await page.getByTestId("remove-opener").click();
  await expect(page.getByTestId("remove-opener")).toHaveCount(0);
  const card = page.getByTestId("action-feedback");
  await card.getByRole("button").focus();
  await page.keyboard.press("Enter");
  await expect(card).toHaveCount(0);
  await expect(page.getByTestId("draft")).toBeFocused();
});

test("unread chat notice joins the host, pauses for focus and opens the inbox", async ({ page }) => {
  await open(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.getByTestId("chat").click();
  await page.clock.runFor(1);
  const group = page.locator('[data-notification-group="messages"]');
  const notice = group.locator(".platforma-status-notice");
  await expect(notice).toBeVisible();
  await page.clock.runFor(250);
  const action = notice.getByRole("button").last();
  await action.focus();
  await page.mouse.move(0, 0);
  await page.clock.runFor(7000);
  await expect(notice).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("route")).toHaveText("/app/conversations?unread=true");
  await page.clock.runFor(201);
  await expect(notice).toHaveCount(0);
});

for (const interaction of ["hover", "focus", "action"] as const) {
  test(`overflow preserves ${interaction} and pending messages do not expire unseen`, async ({ page }) => {
    await open(page);
    await page.clock.install();
    await page.clock.pauseAt(new Date());
    await page.getByTestId(interaction === "action" ? "retry" : "short").click();
    await page.clock.runFor(250);
    const active = page.getByTestId("action-feedback").filter({ hasText: interaction === "action" ? "Повторить" : "Сохранено" });
    await page.getByTestId("delayed-queue").click();
    if (interaction === "hover") await active.hover();
    if (interaction === "focus") await active.getByRole("button").focus();
    if (interaction === "action") {
      await active.getByTestId("action-feedback-action").click();
      await page.getByTestId("draft").focus();
      await page.mouse.move(0, 0);
    }
    await page.clock.runFor(2000);
    await expect(active).toBeVisible();
    await expect(page.getByTestId("action-feedback")).toHaveCount(4);
    await expect(page.getByTestId("notification-host")).not.toContainText("Burst 3");
    if (interaction === "focus") await expect(active.getByRole("button")).toBeFocused();
    if (interaction === "action") {
      await expect(page.getByTestId("counts")).toHaveText("1,0,0");
      await page.getByTestId("release").click();
    } else {
      await active.getByRole("button").click();
    }
    await page.clock.runFor(201);
    await expect(active).toHaveCount(0);
    await expect(page.getByTestId("notification-host")).toContainText("Burst 3");
  });
}

test("queued duplicates collapse and reading time starts on admission", async ({ page }) => {
  await open(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.getByTestId("queue").click();
  await page.getByTestId("queued-short").click();
  await page.getByTestId("queued-short").click();
  await page.clock.runFor(2000);
  const cards = page.getByTestId("action-feedback");
  const pending = cards.filter({ hasText: "Pending short" });
  await expect(pending).toHaveCount(0);
  await cards.filter({ hasText: "Queue 3" }).getByRole("button").click();
  await page.clock.runFor(201);
  await expect(cards.last()).toContainText("Queue 4");
  await cards.filter({ hasText: "Queue 2" }).getByRole("button").click();
  await page.clock.runFor(201);
  await expect(pending).toBeVisible();
  await page.clock.runFor(450);
  await page.mouse.move(0, 0);
  await page.getByTestId("draft").focus();
  await page.clock.runFor(799);
  await expect(pending.locator('xpath=ancestor::div[contains(@class,"platforma-notification-card")][1]')).not.toHaveAttribute("data-leaving", "true");
  await page.clock.runFor(2);
  await expect(pending.locator('xpath=ancestor::div[contains(@class,"platforma-notification-card")][1]')).toHaveAttribute("data-leaving", "true");
  await page.clock.runFor(201);
  await expect(pending).toHaveCount(0);
  await expect(cards).toHaveCount(3);
});

for (const language of ["ru", "kk", "en"]) {
  test(`error classification matches inline and toast ${language}`, async ({ page }) => {
    await page.setViewportSize({ width: language === "ru" ? 1440 : language === "kk" ? 768 : 390, height: 1000 });
    await open(page, language);
    for (const category of ["authentication", "permission", "conflict", "rate_limit", "offline", "provider", "not_found", "validation", "internal", "temporary"]) {
      await page.getByTestId("error-category").selectOption(category);
      const tone = category === "not_found" ? "info" : ["validation", "internal", "temporary"].includes(category) ? "danger" : "warning";
      await expect(page.getByTestId("error-inline").locator("[data-notice-tone]")).toHaveAttribute("data-notice-tone", tone);
      for (const source of ["error-direct", "error-feedback", "error-override"]) {
        await page.getByTestId(source).click();
        const toast = page.getByTestId("action-feedback");
        await expect(toast).toHaveAttribute("data-notice-tone", source === "error-override" ? "danger" : tone);
        if (category === "conflict" && source === "error-direct") {
          await page.screenshot({ path: path.join(evidence, `error-${language}.png`), animations: "disabled" });
        }
        await toast.getByRole("button").first().click();
        await expect(toast).toHaveCount(0);
      }
    }
  });
}

test("enlarged notification text reflows at 320px and closes by keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await open(page);
  await page.getByTestId("long").click();
  await page.addStyleTag({ content: ".platforma-notice-title,.platforma-notice-description { font-size: 28px; line-height: 42px; }" });
  const card = page.getByTestId("action-feedback");
  expect(await card.evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await card.getByRole("button").focus();
  await expect(card.getByRole("button")).toBeInViewport();
  await page.screenshot({ path: path.join(evidence, "text200-320.png"), animations: "disabled" });
  const details = page.locator('.platforma-notification-details');
  await details.click();
  const dialog = page.getByTestId('notification-details');
  await expect(dialog).toBeVisible();
  await dialog.locator('.platforma-notice-description').scrollIntoViewIfNeeded();
  expect(await dialog.locator('.platforma-notice-description').evaluate(node => node.scrollWidth <= node.clientWidth)).toBe(true);
  await page.screenshot({ path: path.join(evidence, "text200-bottom-320.png"), animations: "disabled" });
  await page.keyboard.press('Escape');
  await expect(details).toBeFocused();
  await card.getByRole("button").focus();
  await page.keyboard.press("Enter");
  await expect(card).toHaveCount(0);
  await expect(page.getByTestId("long")).toBeFocused();
});

test("full reading interval resumes after hover and focus, followed by exit", async ({ page }) => {
  await open(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.getByTestId("short").click();
  const card = page.getByTestId("action-feedback");
  await page.clock.runFor(250);
  await card.hover();
  await page.clock.runFor(1200);
  await expect(card).toHaveCount(1);
  await page.keyboard.press("Tab");
  await card.getByRole("button").focus();
  await page.mouse.move(0, 0);
  await page.clock.runFor(1200);
  await expect(card).toHaveCount(1);
  await page.getByTestId("draft").focus();
  await page.clock.runFor(799);
  await expect(card.locator('xpath=ancestor::div[contains(@class,"platforma-notification-card")][1]')).not.toHaveAttribute("data-leaving", "true");
  await page.clock.runFor(2);
  await expect(card.locator('xpath=ancestor::div[contains(@class,"platforma-notification-card")][1]')).toHaveAttribute("data-leaving", "true");
  await page.clock.runFor(199);
  await expect(card).toHaveCount(1);
  await page.clock.runFor(2);
  await expect(card).toHaveCount(0);
});

test("pending action executes once and failed retry remains usable", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await open(page);
  await page.getByTestId("retry").click();
  const action = page.getByTestId("action-feedback-action");
  await action.click();
  await expect(action).toBeDisabled();
  await page.getByTestId("draft").focus();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(1100);
  await expect(action).toBeVisible();
  await expect(page.getByTestId("counts")).toHaveText("1,0,0");
  await page.getByTestId("release").click();
  await expect(action).toHaveCount(0);
  await page.getByTestId("retry-failure").click();
  await action.click();
  await expect(action).toBeEnabled();
  await action.click();
  await expect(page.getByTestId("counts")).toHaveText("3,0,0");
  expect(errors).toEqual([]);
});

test("failed undo offers recovery without repeating the mutation", async ({ page }) => {
  await open(page);
  await page.getByTestId("undo").click();
  const action = page.getByTestId("action-feedback-action");
  await action.click();
  await expect(page.getByTestId("counts")).toHaveText("0,1,0");
  await expect(action).toHaveText("Обновить");
  await action.click();
  await expect(action).toHaveCount(0);
  await expect(page.getByTestId("counts")).toHaveText("0,1,1");
});

for (const kind of ["modal", "drawer", "nested"] as const) {
  test(`toast keyboard actions remain inside ${kind}`, async ({ page }) => {
    await open(page);
    await page.getByTestId(kind === "drawer" ? "drawer" : "modal").click();
    if (kind === "nested") await page.getByTestId("nested").click();
    const opener = page.getByTestId(`${kind}-toast`);
    await opener.click();
    const host = page.getByTestId("notification-host");
    const dialog = page.getByTestId(kind === "nested" ? "nested-modal" : `test-${kind}`);
    await expect(dialog.locator('[data-testid="notification-host"]')).toHaveCount(1);
    const close = host.getByTestId("action-feedback").getByRole("button");
    for (let i = 0; i < 8 && !(await close.evaluate(node => node === document.activeElement)); i++) await page.keyboard.press("Tab");
    await expect(close).toBeFocused();
    await expect(close).toBeInViewport();
    await page.keyboard.press("Enter");
    await expect(host.getByTestId("action-feedback")).toHaveCount(0);
    await expect(opener).toBeFocused();
    await expect(dialog).toBeVisible();
  });
}

test("dismissed network episode stays hidden across identical probes and returns on a new problem", async ({ page, context }) => {
  await open(page);
  await page.unroute("**/ready/");
  let healthy = false;
  await page.route("**/ready/", route => route.fulfill({ status: healthy ? 200 : 503, json: { status: "ok" } }));
  await context.setOffline(true);
  await expect(page.getByTestId("connectivity-banner")).toBeVisible();
  await context.setOffline(false);
  const card = page.getByTestId("connectivity-banner");
  await expect(card).toContainText("пока не восстановлена");
  await card.getByRole("button", { name: "Закрыть" }).click();
  await expect(card).toHaveCount(0);
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await page.waitForTimeout(400);
  await expect(card).toHaveCount(0);
  healthy = true;
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  await expect(page.getByTestId("reads")).toHaveText("2");
  await context.setOffline(true);
  await expect(card).toBeVisible();
  await expect(page.getByTestId("draft")).toHaveValue("Preserved draft");
});

test("reduced motion removes animations and forced colors preserves controls", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce", forcedColors: "active" });
  await open(page, "en");
  await page.getByTestId("show").click();
  const card = page.getByTestId("notification-host").getByTestId("action-feedback");
  expect(await card.locator('xpath=ancestor::div[contains(@class,"platforma-notification-card")][1]').evaluate(node => getComputedStyle(node).animationName)).toBe("none");
  expect(await card.evaluate(node => getComputedStyle(node).borderTopStyle)).toBe("solid");
  await page.keyboard.press("Tab");
  await card.getByRole("button").focus();
  expect(await card.getByRole("button").evaluate(node => getComputedStyle(node).outlineStyle)).toBe("solid");
  await page.screenshot({ path: path.join(evidence, "forced-colors.png") });
  await page.keyboard.press("Enter");
  await expect(card).toHaveCount(0);
});
