import { expect, test } from "@playwright/test";
import { crmSession } from "./support/crm-workspace";
import { ru } from "../src/lib/i18n/ru";
import { kk } from "../src/lib/i18n/kk";
import { en } from "../src/lib/i18n/en";
import type { CustomFieldDefinition } from "../src/types";

test.beforeEach(() => { test.skip(process.env.ZANI_QUALITY_GATE !== "1", "Disposable fixtures required"); test.setTimeout(150_000); });
for (const [locale, copy] of [["ru", ru], ["kk", kk], ["en", en]] as const) {
  test(`multilingual field creation, retry and stable identity ${locale}`, async ({ page }, info) => {
    const s = await crmSession(page);
    if (locale === "ru") {
      const api = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000";
      const data = { business: s.business, entity_type: "client", label: "Concurrent field" };
      const automatic = await Promise.all([0, 1].map(() => page.request.post(`${api}/api/custom-fields/`, { headers: s.headers, data })));
      expect(automatic.map(response => response.status())).toEqual([201, 201]);
      const keys = await Promise.all(automatic.map(async response => (await response.json()).key));
      expect(keys[0]).not.toBe(keys[1]);
      const key = `parallel_${Date.now()}`;
      const explicit = await Promise.all([0, 1].map(() => page.request.post(`${api}/api/custom-fields/`, { headers: s.headers, data: { ...data, key } })));
      expect(explicit.map(response => response.status()).sort()).toEqual([201, 400]);
      const duplicate = await explicit.find(response => response.status() === 400)!.json();
      expect(duplicate).toHaveProperty("key");
    }
    await page.evaluate(value => localStorage.setItem("ai_smb_language", value), locale);
    await page.goto("/app/settings#custom-fields");
    const panel = page.locator("#custom-fields");
    const drawer = page.getByRole("dialog");
    const stamp = Date.now();
    const labels = [`QA Первое поле ${stamp}`, `QA Второе поле ${stamp}`, `Қосымша өріс ${stamp}`, `Название ${stamp}`];
    const fields: CustomFieldDefinition[] = [];
    for (const [index, label] of labels.entries()) {
      await panel.getByRole("button", { name: copy["settings.redesign.addField"], exact: true }).click();
      const input = drawer.getByLabel(copy["settings.redesign.name"], { exact: true });
      await input.fill(label);
      const save = drawer.getByRole("button", { name: copy["settings.add"], exact: true });
      if (index === 0) {
        await page.route("**/api/custom-fields/", route => route.request().method() === "POST"
          ? route.fulfill({ status: 503, json: { detail: "Temporary test outage" } }) : route.continue(), { times: 1 });
        await save.click();
        await expect(drawer.getByRole("alert")).toBeVisible();
        await expect(input).toHaveValue(label);
        await page.screenshot({ path: info.outputPath(`field-retry-${locale}.png`), fullPage: true });
      }
      const response = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith("/api/custom-fields/") && r.status() === 201);
      await save.click();
      const created = await response;
      expect(created.request().postDataJSON()).not.toHaveProperty("key");
      fields.push(await created.json());
      await expect(drawer).toHaveCount(0);
      await expect(panel.getByRole("button", { name: label, exact: true })).toBeVisible();
    }
    expect(new Set(fields.map(field => field.key)).size).toBe(labels.length);
    for (const field of fields) expect(field.key).toMatch(/^[a-zA-Z0-9_-]{1,64}$/);
    await panel.getByRole("button", { name: labels[1], exact: true }).click();
    await drawer.locator("summary").click();
    const technicalKey = drawer.getByRole("textbox", { name: new RegExp(`^${copy["settings.fieldKey"]}`) });
    await technicalKey.fill(fields[0].key);
    await drawer.getByRole("button", { name: copy["common.save"], exact: true }).click();
    await expect(technicalKey).toHaveAttribute("aria-invalid", "true");
    await expect(drawer.getByText(copy["settings.duplicateFieldKey"], { exact: true })).toBeVisible();
    await drawer.getByText(copy["settings.duplicateFieldKey"], { exact: true }).scrollIntoViewIfNeeded();
    await expect(drawer.getByLabel(copy["settings.redesign.name"], { exact: true })).toHaveValue(labels[1]);
    await page.screenshot({ path: info.outputPath(`duplicate-key-${locale}.png`), fullPage: true });
    await technicalKey.fill(fields[1].key);
    await drawer.getByRole("button", { name: copy["common.save"], exact: true }).click();
    await expect(drawer).toHaveCount(0);
    const client = await s.create<{ id: number }>("clients", { full_name: `Field client ${stamp}` });
    await s.action("custom-field-values/bulk-upsert", { business: s.business, entity_type: "client", entity_id: String(client.id), values: [{ definition: fields[0].id, value_json: { value: "Preserved value" } }] });
    await panel.getByRole("button", { name: labels[0], exact: true }).click();
    const renamed = `Переименованное поле ${stamp}`;
    await drawer.getByLabel(copy["settings.redesign.name"], { exact: true }).fill(renamed);
    await drawer.getByRole("button", { name: copy["common.save"], exact: true }).click();
    await expect(drawer).toHaveCount(0);
    const result = await s.read(`custom-fields/${fields[0].id}`);
    expect(result.key).toBe(fields[0].key);
    expect(result.label).toBe(renamed);
    const values = await s.read("custom-field-values", { business: s.business, definition: fields[0].id });
    expect(values.results[0].value_json.value).toBe("Preserved value");
    await page.reload();
    await expect(panel.getByRole("button", { name: renamed, exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`fields-saved-${locale}.png`), fullPage: true });
  });
}
