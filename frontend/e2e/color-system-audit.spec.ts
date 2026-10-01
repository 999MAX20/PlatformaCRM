import fs from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { routes } from "../scripts/audit-color-system.mjs";
import { routeActionRegistry } from "./certification/route-action-registry.mjs";
import { crmSession } from "./support/crm-workspace";

const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
const password = process.env.E2E_PASSWORD || "ZaniTest123!";

test.beforeEach(({}, testInfo) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Requires the disposable runtime");
  test.skip(testInfo.project.name === "tablet-chromium", "Whole-route sweep uses desktop/mobile; targeted CRM tests cover tablet");
  test.setTimeout(600_000);
});

type Observation = { route: string; actualUrl: string; screenshot: string; state: string; alerts: string[]; colors: string[]; oldPalette: string[]; overflow: number; contrast: Array<{ selector: string[]; summary?: string }>; note?: string };

async function observe(page: Page, route: string, testInfo: TestInfo, key: string, note?: string): Promise<Observation> {
  await page.goto(route);
  await expect(page.locator("body")).not.toBeEmpty();
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
  await page.evaluate(() => document.fonts.ready);
  const busy = page.locator('main [role="status"][aria-busy="true"]');
  await expect(busy).toHaveCount(0, { timeout: 15_000 });
  const observed = await page.evaluate(() => {
    const colors = new Set<string>();
    for (const node of document.querySelectorAll("body *")) {
      const box = node.getBoundingClientRect();
      if (!box.width || !box.height) continue;
      const style = getComputedStyle(node);
      if (style.visibility === "hidden" || style.display === "none") continue;
      for (const property of ["color", "backgroundColor", "borderColor", "fill", "stroke"] as const) colors.add(style[property]);
    }
    const oldColors = new Set(["rgb(245, 179, 122)", "rgb(238, 153, 90)", "rgb(247, 243, 238)", "rgb(244, 238, 231)", "rgb(230, 221, 210)", "rgb(194, 65, 12)"]);
    return {
      colors: [...colors].sort(), oldPalette: [...colors].filter((color) => oldColors.has(color)),
      alerts: [...document.querySelectorAll('[role="alert"]')].map((node) => node.textContent?.trim() || ""),
      state: document.querySelector('[data-testid="forbidden-state"]') ? "forbidden" : "rendered",
      overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
    };
  });
  const screenshot = `${key.replace(/[^a-z0-9_-]/gi, "-")}.png`;
  await page.screenshot({ path: testInfo.outputPath(screenshot), fullPage: true, animations: "disabled" });
  const contrast = (await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze()).violations.flatMap((violation) => violation.nodes.map((node) => ({ selector: node.target.map(String), summary: node.failureSummary })));
  return { route, actualUrl: new URL(page.url()).pathname + new URL(page.url()).hash, screenshot, note, contrast, ...observed };
}

async function save(testInfo: TestInfo, observations: Observation[]) {
  const content = JSON.stringify({ viewport: testInfo.project.name, observations }, null, 2);
  fs.writeFileSync(testInfo.outputPath("route-observations.json"), content);
  await testInfo.attach("route-observations", { body: content, contentType: "application/json" });
  expect(observations.flatMap((observation) => observation.oldPalette.map((color) => `${observation.route}: ${color}`))).toEqual([]);
  expect(observations.flatMap((observation) => observation.contrast.map((finding) => ({ route: observation.route, ...finding })))).toEqual([]);
}

test("public routes retain the shared palette, including invalid-link and unchallenged MFA states", async ({ page }, testInfo) => {
  const observations: Observation[] = [];
  const publicPaths = ["/", "/login", "/signup", "/forgot-password", "/reset-password/audit/invalid", "/invite/invalid", "/mfa", "/documents", ...["terms", "privacy", "personal-data", "company-data"].map((id) => `/documents/${id}`), "/documents/unknown", "/not-an-existing-route", "/pricing", "/bots", "/crm", "/contacts"];
  try {
    for (const route of publicPaths) observations.push(await observe(page, route, testInfo, route, /invalid|mfa/.test(route) ? "Invalid link / no pending challenge; successful flows require their own fixture tests" : undefined));
  } finally { await save(testInfo, observations); }
});

for (const role of ["owner", "administrator", "manager", "operator", "specialist"]) {
  test(`${role} route palette and actual permitted or forbidden surfaces`, async ({ page }, testInfo) => {
    const session = await crmSession(page, `business_${role}@example.com`);
    const observations: Observation[] = [];
    const detailIds: Record<string, number> = {};
    if (role === "owner") {
      const client = await session.create<{ id: number }>("clients", { full_name: `Color audit ${testInfo.project.name}`, source: "manual" });
      await session.create("leads", { client: client.id, source: "manual", responsible_user: session.userId, message: "Color audit fixture" });
      await session.create("tasks", { client: client.id, title: "Color audit task", assignee: session.userId });
      const pipeline = (await session.list<{ id: number }>("pipelines"))[0];
      const stage = (await session.list<{ id: number; pipeline: number; is_won: boolean; is_lost: boolean }>("pipeline-stages")).find((item) => item.pipeline === pipeline.id && !item.is_won && !item.is_lost)!;
      await session.create("deals", { client: client.id, pipeline: pipeline.id, stage: stage.id, title: "Color audit deal", owner: session.userId, amount: "100" });
    }
    for (const [segment, endpoint] of Object.entries({ leads: "leads", clients: "clients", deals: "deals", tasks: "tasks", calendar: "appointments", conversations: "inbox/conversations", bots: "bots", "ai-agents": "bots" })) {
      const response = await page.request.get(`${api}/api/${endpoint}/`, { headers: session.headers });
      if (response.ok()) {
        const body = await response.json();
        detailIds[segment] = (body.results || body)[0]?.id;
      }
    }
    try {
      for (const entry of routes.filter((entry) => entry.group === "merchant")) {
        const segment = entry.route.split("/")[2];
        const id = detailIds[segment];
        const route = entry.route.replace(":id", String(id || 999999999)).replace(":section", "profile");
        const missing = entry.route.includes(":id") && !id;
        observations.push(await observe(page, route, testInfo, entry.route, missing ? "No accessible seeded entity: missing/forbidden state only" : undefined));
      }
      if (role === "owner") {
        for (const section of ["business-profile", "team-access", "roles", "security-center", "appointment-messages", "notification-preferences", "quick-replies", "billing", "usage", "custom-fields"]) {
          observations.push(await observe(page, `/app/settings#${section}`, testInfo, `settings-${section}`, "Section navigation, no external setup action executed"));
        }
      }
    } finally { await save(testInfo, observations); }
  });
}

test("platform routes use semantic colors without executing operational actions", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.locator('form input[type="email"]').fill("platform_admin@example.com");
  await page.locator('form input[type="password"]').fill(password);
  await page.locator('form button[type="submit"]').click();
  await expect(page).toHaveURL(/\/platform/);
  const observations: Observation[] = [];
  try {
    for (const entry of routes.filter((entry) => entry.group === "platform")) {
      const route = entry.route.replace(":id", "1");
      observations.push(await observe(page, route, testInfo, entry.route, entry.component === "PlatformPlaceholderPage" ? "Existing platform placeholder, not a completed business workflow" : undefined));
    }
  } finally { await save(testInfo, observations); }
});

test("legacy route aliases are explicitly represented in the existing certification registry", () => {
  const registered = new Set(routeActionRegistry.flatMap((entry) => [entry.route, ...(entry.aliases || []), ...(entry.routerPaths || [])]));
  const legacy = routes.filter((entry) => entry.group === "legacy");
  expect(legacy.length).toBeGreaterThan(0);
  for (const entry of legacy) expect(registered.has(entry.route), entry.route).toBeTruthy();
});
