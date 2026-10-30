import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";

test("pricing draft survives failed save and safety commands refresh their own state", async ({ page }) => {
  test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable authentication fixture required");
  const session = await crmSession(page);
  let failSave = true;
  const writes: Array<{ path: string; body: Record<string, unknown> }> = [];
  const rules: Record<string, unknown>[] = [];
  const control = { id: 1, business: session.business, emergency_stop_enabled: false, emergency_stop_reason: "" };
  await page.route("**/api/pricing/kaspi/**", async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname;
    if (request.method() !== "GET") {
      const body = request.postDataJSON(); writes.push({ path, body });
      if (path.endsWith("/rules/")) {
        if (failSave) return route.fulfill({ status: 503, json: { detail: "Pricing fixture unavailable" } });
        const rule = { ...body, id: 10, status: "active", config_json: {}, last_error: "", autopilot_confirmed_at: null };
        rules.push(rule); return route.fulfill({ status: 201, json: rule });
      }
      if (path.endsWith("/control/emergency-stop/")) { control.emergency_stop_enabled = true; control.emergency_stop_reason = String(body.reason); return route.fulfill({ json: control }); }
      if (path.endsWith("/control/resume/")) { control.emergency_stop_enabled = false; return route.fulfill({ json: control }); }
      throw new Error(`Unexpected pricing command: ${path}`);
    }
    if (path.endsWith("/control/current/")) return route.fulfill({ json: control });
    if (path.endsWith("/rules/")) return route.fulfill({ json: rules });
    return route.fulfill({ json: [] });
  });
  await page.goto("/app/pricing");
  const form = page.locator("section").filter({ has: page.getByRole("heading", { name: ru["pricing.newRule"], exact: true }) });
  await form.getByLabel("SKU", { exact: true }).fill("REFACTOR-1");
  await form.getByLabel(ru["pricing.name"], { exact: true }).fill("Pricing fixture");
  await form.getByLabel(ru["pricing.currentPrice"], { exact: true }).fill("1200");
  await form.getByLabel(ru["pricing.minPrice"], { exact: true }).fill("1000");
  const save = form.getByRole("button", { name: ru["pricing.createRule"], exact: true });
  await save.focus(); await page.keyboard.press("Enter");
  await expect.poll(() => writes.length).toBe(1);
  await expect(save).toBeEnabled();
  await expect(form.getByLabel("SKU", { exact: true })).toHaveValue("REFACTOR-1");
  await expect(form.getByLabel(ru["pricing.minPrice"], { exact: true })).toHaveValue("1000");
  failSave = false; await save.click();
  await expect(form.getByLabel("SKU", { exact: true })).toHaveValue("");
  await expect(page.getByText("Pricing fixture", { exact: true })).toBeVisible();
  expect(writes[0].body).toEqual(writes[1].body);
  expect(writes[1].body).toMatchObject({ business: session.business, current_price: "1200", min_price: "1000", mode: "approval" });
  await page.getByRole("button", { name: ru["pricing.stopAgent"], exact: true }).click();
  await expect(page.getByRole("button", { name: ru["pricing.resume"], exact: true })).toBeVisible();
  await page.getByRole("button", { name: ru["pricing.resume"], exact: true }).click();
  await expect(page.getByRole("button", { name: ru["pricing.stopAgent"], exact: true })).toBeVisible();
  expect(writes.slice(2).map(write => write.body.business)).toEqual([session.business, session.business]);
});
