import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";

test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required"); test.setTimeout(150_000); });
for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`client custom filters ${locale}`, async ({ page }, info) => {
    const s = await crmSession(page);
    const stamp = `QA006${Date.now()}`;
    const first = await s.create<{ id: number }>("clients", { full_name: `${stamp} Match`, source: "manual" });
    await s.create("clients", { full_name: `${stamp} Empty`, source: "manual" });
    const fields: { id: number; label: string; kind: string; value: string }[] = [];
    for (const [kind, value] of [["text", "Alpha"], ["number", "12"], ["select", "A"], ["date", "2026-11-21"]]) {
      const field = await s.create<{ id: number; label: string }>("custom-fields", { entity_type: "client", label: `${stamp} ${kind}`, field_type: kind, options_json: { display: { in_filters: true }, ...(kind === "select" ? { options: ["A", "B"] } : {}) } });
      await s.action("custom-field-values/bulk-upsert", { business: s.business, entity_type: "client", entity_id: String(first.id), values: [{ definition: field.id, value_json: { value } }] });
      fields.push({ ...field, kind, value });
    }
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto(`/app/clients?search=${stamp}&source=manual&page=3`);
    const toolbar = page.getByTestId("clients-unified-toolbar");
    const trigger = toolbar.getByRole("button", { name: new RegExp(`^${copy["crmFilters.filters"]}`) });
    const panel = page.getByTestId("clients-filters-panel");
    const choose = async (label: string, option: string) => {
      await expect(panel.getByRole("combobox", { name: new RegExp(`^${label}`) })).toBeVisible();
      await panel.getByRole("combobox", { name: new RegExp(`^${label}`) }).click();
      await panel.getByRole("option", { name: option, exact: true }).click();
    };
    const apply = async (field: number, operator: string, count: number) => {
      const pending = page.waitForResponse(r => {
        const url = new URL(r.url());
        return url.pathname === "/api/clients/" && url.searchParams.get("custom_field") === String(field) && url.searchParams.get("custom_operator") === operator && r.status() === 200;
      });
      await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
      const response = await pending;
      const result = await response.json();
      expect(result.count).toBe(count);
      expect(result.summary.total).toBe(count);
      expect(new URL(response.url()).searchParams.get("page")).toBe("1");
      await expect(panel).toHaveCount(0);
      await expect(page).toHaveURL(new RegExp(`custom_field=${field}`));
      expect(new URL(page.url()).searchParams.get("source")).toBe("manual");
      expect(new URL(page.url()).searchParams.has("page")).toBe(false);
    };
    for (const field of fields) {
      await trigger.click();
      await choose(copy["importWorkspace.customFilter"], field.label);
      const operator = field.kind === "number" ? "gte" : field.kind === "date" ? "lte" : "equals";
      await choose(copy["importWorkspace.operator"], copy[`importWorkspace.${operator}`]);
      await panel.getByLabel(copy["importWorkspace.value"], { exact: true }).fill(field.value);
      await panel.screenshot({ path: info.outputPath(`${locale}-${field.kind}-filter.png`) });
      await apply(field.id, operator, 1);
      await expect(page.getByRole("button", { name: new RegExp(`${stamp} Match`) })).toBeVisible();
      await page.reload();
      await trigger.click();
      await expect(panel.getByLabel(copy["importWorkspace.value"], { exact: true })).toHaveValue(field.value);
      await page.keyboard.press("Escape");
      await expect(panel).toHaveCount(0);
      await expect(trigger).toBeFocused();
    }
    await trigger.click();
    await choose(copy["importWorkspace.customFilter"], fields[0].label);
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(panel.getByRole("alert")).toBeVisible();
    await choose(copy["importWorkspace.operator"], copy["importWorkspace.is_empty"]);
    await apply(fields[0].id, "is_empty", 1);
    await expect(page.getByRole("button", { name: new RegExp(`${stamp} Empty`) })).toBeVisible();
    await trigger.click();
    await choose(copy["importWorkspace.operator"], copy["importWorkspace.equals"]);
    await panel.getByLabel(copy["importWorkspace.value"], { exact: true }).fill("No match");
    await apply(fields[0].id, "equals", 0);
    await page.screenshot({ path: info.outputPath(`${locale}-empty.png`) });
    await trigger.click();
    await choose(copy["importWorkspace.customFilter"], copy["importWorkspace.choose"]);
    await panel.getByRole("button", { name: copy["crmFilters.apply"], exact: true }).click();
    await expect(page).not.toHaveURL(/custom_field=/);
    await expect(page.getByRole("button", { name: new RegExp(`${stamp} Match`) })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/custom_field=/);
    await page.goForward();
    await expect(page).not.toHaveURL(/custom_field=/);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test("client custom filter request error retains URL and retries", async ({ page }, info) => {
  const s = await crmSession(page);
  const stamp = `QA006Recovery${Date.now()}`;
  const client = await s.create<{ id: number }>("clients", { full_name: stamp, source: "manual" });
  const field = await s.create<{ id: number }>("custom-fields", { entity_type: "client", label: stamp, field_type: "text", options_json: { display: { in_filters: true } } });
  await s.action("custom-field-values/bulk-upsert", { business: s.business, entity_type: "client", entity_id: String(client.id), values: [{ definition: field.id, value_json: { value: "Alpha" } }] });
  await page.evaluate(() => localStorage.setItem("ai_smb_language", "ru"));
  await page.route("**/api/clients/?**", route => route.fulfill({ status: 503, json: { detail: "Temporary test failure" } }));
  const url = `/app/clients?source=manual&search=${stamp}&custom_field=${field.id}&custom_operator=equals&custom_value=Alpha`;
  await page.goto(url);
  const retry = page.getByRole("button", { name: ru["common.retry"], exact: true });
  await expect(retry).toBeVisible({ timeout: 30_000 });
  expect(new URL(page.url()).searchParams.get("custom_value")).toBe("Alpha");
  await page.screenshot({ path: info.outputPath("request-error.png") });
  await page.unroute("**/api/clients/?**");
  await retry.click();
  await expect(page.getByRole("button", { name: new RegExp(stamp) })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("source")).toBe("manual");
  const trigger = page.getByTestId("clients-unified-toolbar").getByRole("button", { name: /^Фильтры/ });
  await trigger.focus();
  await page.keyboard.press("Enter");
  const panel = page.getByTestId("clients-filters-panel");
  await expect(panel.getByLabel(ru["importWorkspace.value"], { exact: true })).toHaveValue("Alpha");
  const fieldControl = panel.getByRole("combobox", { name: new RegExp(`^${ru["importWorkspace.customFilter"]}`) });
  await fieldControl.focus();
  await page.keyboard.press("Enter");
  await expect(panel.getByRole("listbox")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(panel).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(trigger).toBeFocused();
});
