import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { routes } from "../scripts/audit-color-system.mjs";

test.beforeEach(({}, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires the disposable runtime");
  test.skip(testInfo.project.name === "tablet-chromium", "Route/state audit uses desktop/mobile; workspace and typography suites cover tablet");
  test.setTimeout(180_000);
});

async function capture(page: Page, testInfo: TestInfo, name: string) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  const mobileNav = page.locator("nav.fixed");
  if (await mobileNav.isVisible()) await expect(mobileNav).toHaveCSS("background-color", "rgba(255, 255, 255, 0.96)");
  const result = await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze();
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true, animations: "disabled" });
  const evidence = { url: page.url(), violations: result.violations };
  fs.writeFileSync(testInfo.outputPath(`${name}.json`), JSON.stringify(evidence, null, 2));
  expect(result.violations, name).toEqual([]);
}

test("real create, edit and archive dialogs retain semantic actions and readable content", async ({ page }, testInfo) => {
  const session = await crmSession(page);
  const client = await session.create<{ id: number }>("clients", { full_name: "Palette dialog fixture", source: "manual" });
  await page.goto(`/app/leads?create=1&client=${client.id}`);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("lead-action-submit")).toHaveCSS("background-color", "rgb(0, 122, 89)");
  await capture(page, testInfo, "create-lead");
  await page.keyboard.press("Escape");
  await page.goto(`/app/clients/${client.id}`);
  await page.getByTestId("client-edit-action").click();
  await expect(dialog.locator('input[name="full_name"]')).toHaveValue("Palette dialog fixture");
  await expect(dialog.getByTestId("client-action-submit")).toHaveCSS("background-color", "rgb(0, 122, 89)");
  await capture(page, testInfo, "edit-client");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await page.getByRole("button", { name: "Архивировать", exact: true }).click();
  const confirm = dialog.getByRole("button", { name: "Архивировать", exact: true });
  await expect(confirm).toBeDisabled();
  await capture(page, testInfo, "archive-disabled");
  await dialog.locator("textarea").fill("Palette fixture reason");
  await expect(confirm).toBeEnabled();
  await expect(confirm).toHaveCSS("background-color", "rgb(255, 245, 232)");
  await expect(confirm).toHaveCSS("color", "rgb(154, 90, 19)");
  await capture(page, testInfo, "archive-ready");
  await page.keyboard.press("Escape");
});

for (const role of ["owner", "administrator", "manager", "operator", "specialist"]) {
  test(`${role} actual conversation and all AI agent sections`, async ({ page }, testInfo) => {
    const session = await crmSession(page, `business_${role}@example.com`);
    for (const [index, route] of ["/app", "/app/dashboard", "/app/leads", "/app/integrations", "/app/automations", "/app/tasks", "/app/account", "/app/analytics", "/app/calendar", "/app/outreach", "/app/services"].entries()) {
      await page.goto(route);
      await capture(page, testInfo, `shared-layout-${index}`);
      if (route === "/app/analytics") {
        for (const details of await page.locator("details").all()) {
          if (await details.getAttribute("open") === null) await details.locator("summary").first().click();
        }
        await capture(page, testInfo, "analytics-expanded");
      }
      const hoverTarget = route === "/app/leads" ? page.locator("button.touch-pan-y").first()
        : route === "/app/dashboard" ? page.locator("a").filter({ has: page.locator(".col-span-3") }).first() : null;
      if (hoverTarget && await hoverTarget.isVisible()) {
        await hoverTarget.hover();
        await capture(page, testInfo, `shared-layout-${index}-hover`);
      }
    }
    const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
    const details: Array<{ endpoint: string; id?: number; status: number }> = [];
    for (const endpoint of ["inbox/conversations", "bots"]) {
      const response = await page.request.get(`${api}/api/${endpoint}/`, { headers: session.headers });
      const body = response.ok() ? await response.json() : null;
      const id = body ? (body.results || body)[0]?.id : undefined;
      details.push({ endpoint, id, status: response.status() });
      const paths = endpoint === "bots"
        ? ["profile", "knowledge", "actions", "channels", "test"].map(section => `/app/ai-agents/${id || 999999999}/${section}`)
        : [`/app/conversations/${id || 999999999}`];
      for (const [index, route] of paths.entries()) {
        await page.goto(route);
        await capture(page, testInfo, `${endpoint.replace("/", "-")}-${index}`);
      }
    }
    fs.writeFileSync(testInfo.outputPath("detail-availability.json"), JSON.stringify(details, null, 2));
  });
}

test("archived service remains readable and a pending local switch uses disabled tokens", async ({ page }, testInfo) => {
  const session = await crmSession(page);
  const name = `Palette archived service ${testInfo.project.name}`;
  const service = await session.create<{ id: number }>("services", { name, duration_minutes: 30, price_from: "100" });
  await session.action(`services/${service.id}/archive`, { reason: "Palette fixture" });
  await page.goto(`/app/services?status=archived&search=${encodeURIComponent(name)}`);
  const row = page.locator('[data-testid="service-row"]:visible').filter({ hasText: name }).first();
  await expect(row).toBeVisible();
  await expect(row).toHaveCSS("opacity", "1");
  await capture(page, testInfo, "archived-service");
  await page.goto("/app/account#notifications");
  const toggle = page.locator('#notifications button[role="switch"]').first();
  await expect(toggle).toBeEnabled();
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/api/notification-preferences/**", async route => {
    if (!["POST", "PATCH"].includes(route.request().method())) return route.continue();
    await pending;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Palette recovery fixture" }) });
  });
  try {
    await toggle.click();
    await expect(toggle).toBeDisabled();
    await expect(toggle.locator('span[aria-hidden="true"]')).toHaveCSS("background-color", "rgb(238, 241, 239)");
    await expect(toggle.locator('span[aria-hidden="true"] > span')).toHaveCSS("background-color", "rgb(114, 128, 120)");
    await page.screenshot({ path: testInfo.outputPath("preference-pending.png"), fullPage: true });
  } finally { release(); }
  await expect(toggle).toBeEnabled();
  await capture(page, testInfo, "preference-recovery");
});

for (const role of ["platform_admin", "platform_manager"]) {
test(`${role} sees readable permitted and denied platform pages`, async ({ page }, testInfo) => {
  expect(process.env.DATABASE_URL).toMatch(/zani-quality-gate-[^/]+\/gate\.sqlite3$/);
  expect(process.env.E2E_PYTHON).toBeTruthy();
  const fixture = spawnSync(process.env.E2E_PYTHON!, ["manage.py", "shell", "-c", [
    "import os",
    "from apps.accounts.models import User",
    "user,_=User.objects.get_or_create(email='palette-platform-manager@example.com',defaults={'username':'palette-platform-manager','role':User.Roles.PLATFORM_MANAGER})",
    "user.set_password(os.environ['E2E_PASSWORD'])",
    "user.save()",
  ].join("; ")], { cwd: path.resolve(process.cwd(), ".."), env: process.env, encoding: "utf8", timeout: 30_000 });
  expect(fixture.status, fixture.stderr || String(fixture.error || "")).toBe(0);
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill(role === "platform_manager" ? "palette-platform-manager@example.com" : "platform_admin@example.com");
  await page.locator('form input[type="password"]').fill(process.env.E2E_PASSWORD!);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/platform/);
  for (const [index, entry] of routes.filter(entry => entry.group === "platform").entries()) {
    await page.goto(entry.route.replace(":id", "1"));
    await capture(page, testInfo, `platform-manager-${index}`);
  }
});
}
