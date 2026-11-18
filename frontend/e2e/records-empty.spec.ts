import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable runtime required");
  test.setTimeout(120_000);
});

const empty = { count: 0, next: null, previous: null, results: [], summary: { planned: 0, completed: 0, cancelled: 0, no_show: 0 } };
for (const [language, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`empty appointment actions and recovery ${language}`, async ({ page }, info) => {
    await page.addInitScript(value => localStorage.setItem("ai_smb_language", value), language);
    await page.route("**/api/auth/me/", async route => {
      const response = await route.fetch(); const user = await response.json();
      await route.fulfill({ response, json: { ...user, preferences: { ...user.preferences, language } } });
    });
    const session = await crmSession(page);
    let mode: "first" | "real" | "failure" = "first";
    await page.route("**/api/appointments/workspace/**", async route => {
      const url = new URL(route.request().url());
      if (!url.searchParams.has("start_from")) {
        expect(url.searchParams.get("business")).toBe(String(session.business));
        expect(url.searchParams.get("page_size")).toBe("1");
        if (mode === "first") return route.fulfill({ json: empty });
        if (mode === "failure") return route.fulfill({ status: 503, json: { detail: "Test read failure" } });
      }
      return route.continue();
    });
    await page.goto("/app/appointments?from=2030-12-15&to=2030-12-15");
    const cta = page.getByTestId("records-empty");
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptyFirst"]);
    await expect(cta).toContainText(copy["records.emptyFirstHint"]);
    await expect(page.getByRole("button", { name: copy["appointments.create"], exact: true })).toHaveCount(1);
    await page.screenshot({ path: info.outputPath(`first-${language}.png`) });
    const create = cta.getByRole("button", { name: copy["appointments.create"], exact: true });
    await create.focus(); await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog", { name: copy["appointments.create"], exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(create).toBeFocused();

    mode = "real";
    await page.reload();
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptyDay"]);
    await expect(page.getByRole("button", { name: copy["appointments.create"], exact: true })).toHaveCount(1);
    await cta.getByRole("button", { name: copy["records.chooseDate"], exact: true }).click();
    const calendar = page.locator("#records-period-panel");
    await expect(calendar).toBeVisible();
    await calendar.locator('[data-date="2030-12-16"]').click();
    await calendar.locator('[data-date="2030-12-17"]').click();
    await calendar.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).toHaveURL(/from=2030-12-16.*to=2030-12-17/);
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptyPeriod"]);
    await page.screenshot({ path: info.outputPath(`period-${language}.png`) });

    await page.getByRole("textbox", { name: copy["records.search"], exact: true }).fill("NO MATCH EMPTY CTA");
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptySearch"]);
    await expect(cta.getByRole("button")).toHaveCount(1);
    await expect(page.getByRole("button", { name: copy["appointments.create"], exact: true })).toHaveCount(0);
    await cta.getByRole("button", { name: copy["records.reset"], exact: true }).click();
    await expect(page).not.toHaveURL(/search=|2030/);
    await page.goto("/app/appointments?from=2030-12-15&to=2030-12-15&workflow=completed");
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptySearch"]);
    await page.screenshot({ path: info.outputPath(`filtered-${language}.png`) });

    mode = "failure";
    await page.goto("/app/appointments?from=2030-12-15&to=2030-12-15");
    await page.reload();
    await expect(page.getByTestId("inline-fallback")).toBeVisible({ timeout: 30000 });
    await expect(cta).toHaveCount(0);
    mode = "real";
    await page.getByTestId("inline-fallback").getByRole("button", { name: copy["common.retry"], exact: true }).click();
    await expect(cta.getByRole("heading")).toHaveText(copy["records.emptyDay"]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    const data = await session.read("appointments/workspace", { business: session.business, page_size: 1 });
    expect(data.count).toBeGreaterThan(0);
    const day = data.results[0].start_at.slice(0, 10);
    await page.goto(`/app/appointments?from=${day}&to=${day}`);
    await expect(page.getByTestId("records-workspace").getByRole("row").or(page.getByTestId("records-workspace").getByRole("button", { name: new RegExp(`#${data.results[0].id}`) })).first()).toBeAttached();
    await expect(cta).toHaveCount(0);
    await expect(page.getByRole("button", { name: copy["appointments.create"], exact: true })).toHaveCount(1);
  });
}

test("read-only user has no create CTA", async ({ page }) => {
  await page.route("**/api/auth/me/", async route => {
    const response = await route.fetch(); const user = await response.json();
    for (const membership of user.memberships) membership.role = "operator";
    for (const key of Object.keys(user.effective_permissions)) user.effective_permissions[key] = user.effective_permissions[key].filter((p: { resource: string; action: string }) => !(p.resource === "appointments" && p.action === "create"));
    await route.fulfill({ response, json: { ...user, preferences: { ...user.preferences, language: "ru" } } });
  });
  await crmSession(page);
  await page.route("**/api/appointments/workspace/**", route => route.fulfill({ json: empty }));
  await page.goto("/app/appointments?from=2030-12-15&to=2030-12-15");
  await expect(page.getByTestId("records-empty").getByRole("heading")).toHaveText(ru["records.emptyNone"]);
  await expect(page.getByRole("button", { name: ru["appointments.create"], exact: true })).toHaveCount(0);
});

test("availability loading and narrow text resize", async ({ page }, info) => {
  await crmSession(page);
  let release!: () => void;
  const ready = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/appointments/workspace/**", async route => {
    if (!new URL(route.request().url()).searchParams.has("start_from")) await ready;
    await route.fulfill({ json: empty });
  });
  await page.goto("/app/appointments?from=2030-12-15&to=2030-12-15");
  await expect(page.getByTestId("records-workspace")).toHaveAttribute("aria-busy", "false");
  await expect(page.getByTestId("records-empty")).toHaveCount(0);
  release();
  const cta = page.getByTestId("records-empty");
  await expect(cta).toBeVisible();
  await page.setViewportSize({ width: 320, height: 640 });
  await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });
  const button = cta.getByRole("button");
  await button.scrollIntoViewIfNeeded();
  await expect(button).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: info.outputPath("narrow-text-resize.png"), fullPage: true });
});
